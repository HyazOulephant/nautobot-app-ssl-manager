"""Helpers to validate certificate data and parse PEM certificates.

Only facts read from the certificate itself are returned: nothing is guessed.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import ExtensionOID, NameOID

from nautobot_ssl_manager.choices import ExtendedKeyUsageChoices, KeyAlgorithmChoices, ValidationLevelChoices

PRIVATE_KEY_MARKER = "PRIVATE KEY"
SAN_EMAIL_PREFIX = "email:"
SAN_URI_PREFIX = "uri:"

_DNS_LABEL_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_HEX_RE = re.compile(r"^[0-9a-f]+$")


class CertificateParseError(ValueError):
    """Raised when a PEM payload cannot be used to describe a certificate."""


#
# Normalization / validation helpers
#


def normalize_hex(value):
    """Normalize a hexadecimal identifier (serial number, fingerprint): lowercase, without separators."""
    if not value:
        return value
    return re.sub(r"[\s:]", "", str(value)).lower()


def is_hex(value):
    """Return True if `value` is a non-empty lowercase hexadecimal string."""
    return bool(value) and bool(_HEX_RE.match(value))


def is_valid_dns_name(value):
    """Return True if `value` is a valid DNS name, optionally starting with a `*.` wildcard label."""
    if not value or len(value) > 253:
        return False
    labels = value.split(".")
    if labels[0] == "*":
        labels = labels[1:]
        if len(labels) < 2:
            return False
    return all(_DNS_LABEL_RE.match(label) for label in labels)


def normalize_san(value):
    """Normalize a single Subject Alternative Name entry. Returns the normalized value or raises ValueError."""
    value = str(value).strip()
    lowered = value.lower()
    if lowered.startswith(SAN_EMAIL_PREFIX):
        address = value[len(SAN_EMAIL_PREFIX) :].strip()
        if "@" not in address:
            raise ValueError(f"'{value}' is not a valid email SAN.")
        return f"{SAN_EMAIL_PREFIX}{address}"
    if lowered.startswith(SAN_URI_PREFIX):
        uri = value[len(SAN_URI_PREFIX) :].strip()
        if not uri:
            raise ValueError(f"'{value}' is not a valid URI SAN.")
        return f"{SAN_URI_PREFIX}{uri}"
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    if is_valid_dns_name(lowered):
        return lowered
    raise ValueError(
        f"'{value}' is not a valid SAN: expected a DNS name, an IP address, 'email:<address>' or 'uri:<uri>'."
    )


def normalize_san_list(values):
    """Normalize and de-duplicate (keeping order) a list of SAN entries. Raises ValueError listing invalid entries."""
    normalized = []
    errors = []
    for value in values or []:
        if not str(value).strip():
            continue
        try:
            entry = normalize_san(value)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if entry not in normalized:
            normalized.append(entry)
    if errors:
        raise ValueError(" ".join(errors))
    return normalized


def is_wildcard_san(value):
    """Return True if the SAN entry is a wildcard DNS name."""
    return str(value).startswith("*.")


#
# PEM parsing
#


@dataclass
class ParsedCertificate:  # pylint: disable=too-many-instance-attributes
    """Facts extracted from a PEM certificate."""

    pem: str
    common_name: str = ""
    subject_alternative_names: list = field(default_factory=list)
    issuer_common_name: str = ""
    serial_number: str = ""
    fingerprint_sha256: str = ""
    not_before: datetime = None
    not_after: datetime = None
    key_algorithm: str = ""
    key_size: int = None
    extended_key_usage: list = field(default_factory=list)
    validation_level: str = ""
    warnings: list = field(default_factory=list)


def _first_attribute(name, oid):
    attributes = name.get_attributes_for_oid(oid)
    return str(attributes[0].value) if attributes else ""


def _is_ca(certificate):
    try:
        return certificate.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value.ca
    except x509.ExtensionNotFound:
        return False


def _select_leaf(certificates):
    """Return the single end-entity certificate of a PEM bundle, or raise if it cannot be determined with certainty."""
    if len(certificates) == 1:
        return certificates[0]
    leaves = [certificate for certificate in certificates if not _is_ca(certificate)]
    if len(leaves) != 1:
        raise CertificateParseError(
            "The PEM contains several certificates and the end-entity certificate cannot be identified with "
            "certainty. Please paste only the certificate to import."
        )
    return leaves[0]


def _parse_sans(certificate, parsed):
    try:
        extension = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
    except x509.ExtensionNotFound:
        return
    for general_name in extension:
        if isinstance(general_name, x509.DNSName):
            value = general_name.value.lower()
        elif isinstance(general_name, x509.IPAddress):
            value = str(general_name.value)
        elif isinstance(general_name, x509.RFC822Name):
            value = f"{SAN_EMAIL_PREFIX}{general_name.value}"
        elif isinstance(general_name, x509.UniformResourceIdentifier):
            value = f"{SAN_URI_PREFIX}{general_name.value}"
        else:
            parsed.warnings.append(f"Unsupported SAN type ignored: {general_name!r}.")
            continue
        if value not in parsed.subject_alternative_names:
            parsed.subject_alternative_names.append(value)


def _parse_key(certificate, parsed):
    public_key = certificate.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        parsed.key_algorithm = KeyAlgorithmChoices.RSA
        parsed.key_size = public_key.key_size
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        parsed.key_algorithm = KeyAlgorithmChoices.ECDSA
        parsed.key_size = public_key.key_size
    elif isinstance(public_key, ed25519.Ed25519PublicKey):
        parsed.key_algorithm = KeyAlgorithmChoices.ED25519
    else:
        parsed.warnings.append(f"Unsupported key algorithm ({type(public_key).__name__}): key fields left empty.")


def _parse_eku(certificate, parsed):
    try:
        extension = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
    except x509.ExtensionNotFound:
        return
    for oid in extension:
        value = ExtendedKeyUsageChoices.OIDS.get(oid.dotted_string)
        if value is None:
            parsed.warnings.append(f"Unsupported Extended Key Usage ignored: {oid.dotted_string}.")
        elif value not in parsed.extended_key_usage:
            parsed.extended_key_usage.append(value)


def _parse_validation_level(certificate, parsed):
    try:
        extension = certificate.extensions.get_extension_for_oid(ExtensionOID.CERTIFICATE_POLICIES).value
    except x509.ExtensionNotFound:
        return
    levels = {
        ValidationLevelChoices.POLICY_OIDS[policy.policy_identifier.dotted_string]
        for policy in extension
        if policy.policy_identifier.dotted_string in ValidationLevelChoices.POLICY_OIDS
    }
    if len(levels) == 1:
        parsed.validation_level = levels.pop()
    elif len(levels) > 1:
        parsed.warnings.append("Several validation level policies found: validation level left empty.")


def parse_pem_certificate(pem_text):
    """Parse a PEM certificate and return a `ParsedCertificate`.

    Raises:
        CertificateParseError: if the PEM contains a private key, is invalid, or is ambiguous.
    """
    pem_text = (pem_text or "").strip()
    if not pem_text:
        raise CertificateParseError("The PEM is empty.")
    if PRIVATE_KEY_MARKER in pem_text.upper():
        raise CertificateParseError(
            "The PEM contains a private key. Private keys must never be stored in Nautobot: "
            "please paste the public certificate only."
        )
    try:
        certificates = x509.load_pem_x509_certificates(pem_text.encode())
    except ValueError as exc:
        raise CertificateParseError(f"Invalid PEM certificate: {exc}") from exc

    certificate = _select_leaf(certificates)
    parsed = ParsedCertificate(pem=certificate.public_bytes(serialization.Encoding.PEM).decode())
    parsed.common_name = _first_attribute(certificate.subject, NameOID.COMMON_NAME)
    parsed.issuer_common_name = _first_attribute(certificate.issuer, NameOID.COMMON_NAME)
    parsed.serial_number = format(certificate.serial_number, "x")
    parsed.fingerprint_sha256 = certificate.fingerprint(hashes.SHA256()).hex()
    parsed.not_before = certificate.not_valid_before_utc
    parsed.not_after = certificate.not_valid_after_utc
    _parse_sans(certificate, parsed)
    _parse_key(certificate, parsed)
    _parse_eku(certificate, parsed)
    _parse_validation_level(certificate, parsed)
    return parsed
