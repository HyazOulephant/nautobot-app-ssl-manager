"""Import of a PEM bundle (full chain): analysis of each certificate, then creation after review.

Only facts are used:

- the chain is established by signature verification (`utils.is_issued_by`), not by the order in the file;
- existing certificates are detected by SHA-256 fingerprint, existing CAs by their linked CA certificate;
- an existing CA with the same name as the one proposed (CA names are unique) is proposed as link target;
- fields that cannot be read from the certificates (CA type, statuses, provider, tenant) are left to the user.
"""

from dataclasses import dataclass, field

from cryptography import x509
from django.core.exceptions import ValidationError
from django.db import transaction
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH

from nautobot_ssl_manager import models, utils

ACTION_NONE = "none"
ACTION_CREATE_CERTIFICATE = "create_certificate"
ACTION_CREATE_CA = "create_ca"
ACTION_LINK_CA = "link_ca"

ROLE_ROOT = "Root CA"
ROLE_INTERMEDIATE = "Intermediate CA"
ROLE_CERTIFICATE = "Certificate"


def find_issuing_authorities(certificate, authorities_with_certificate=None):
    """Certificate Authorities whose stored CA certificate is proven to have issued `certificate` (x509).

    `authorities_with_certificate` is an optional list of `(CertificateAuthority, x509.Certificate)` to avoid loading
    the CA certificates several times.
    """
    if authorities_with_certificate is None:
        authorities_with_certificate = load_authority_certificates()
    issuers = []
    for authority, ca_certificate in authorities_with_certificate:
        if authority not in issuers and utils.is_issued_by(certificate, ca_certificate):
            issuers.append(authority)
    return issuers


def load_authority_certificates():
    """`(CertificateAuthority, x509.Certificate)` for every CA whose CA certificate has a valid PEM."""
    result = []
    queryset = models.CertificateAuthority.objects.filter(certificate__isnull=False).exclude(certificate__pem="")
    for authority in queryset.select_related("certificate"):
        try:
            result.append((authority, x509.load_pem_x509_certificate(authority.certificate.pem.encode())))
        except ValueError:
            continue  # Invalid PEMs are reported by the Certificate validation.
    return result


def default_certificate_name(parsed):
    """Certificate name, as for the single certificate import: Common Name, or first SAN."""
    name = parsed.common_name or (parsed.subject_alternative_names[0] if parsed.subject_alternative_names else "")
    return (name or parsed.subject_dn or parsed.fingerprint_sha256)[:CHARFIELD_MAX_LENGTH]


def default_authority_name(parsed):
    """CA name: Common Name of the CA certificate, or its subject DN."""
    return (parsed.common_name or parsed.subject_dn or parsed.fingerprint_sha256)[:CHARFIELD_MAX_LENGTH]


@dataclass
class BundleEntry:  # pylint: disable=too-many-instance-attributes
    """One certificate of the bundle, what exists in Nautobot and the proposed action."""

    index: int
    parsed: utils.ParsedCertificate
    existing_certificate: models.Certificate = None
    existing_authority: models.CertificateAuthority = None
    named_authority: models.CertificateAuthority = None
    issuer_entry: "BundleEntry" = None
    issuer_authority: models.CertificateAuthority = None
    self_signed: bool = False
    depth: int = 0
    action: str = ACTION_NONE
    disabled_reason: str = ""
    notes: list = field(default_factory=list)

    @property
    def prefix(self):
        """Form field prefix of this entry."""
        return f"entry{self.index}"

    @property
    def is_ca(self):
        """True for a CA certificate (basicConstraints CA:TRUE)."""
        return self.parsed.is_ca

    @property
    def role(self):
        """Role read from the certificate itself."""
        if not self.is_ca:
            return ROLE_CERTIFICATE
        return ROLE_ROOT if self.self_signed else ROLE_INTERMEDIATE

    @property
    def creates_certificate(self):
        """True when the action creates the Certificate (it does not exist yet)."""
        return self.action != ACTION_NONE and self.existing_certificate is None

    @property
    def issuer_label(self):
        """Human readable issuer, as established by signature verification."""
        if self.self_signed:
            return "Self-signed"
        if self.issuer_entry is not None:
            return f"{self.issuer_entry.parsed.common_name or self.issuer_entry.parsed.subject_dn} (in this bundle)"
        if self.issuer_authority is not None:
            return f"{self.issuer_authority} (in Nautobot)"
        return f"Unknown ({self.parsed.issuer_dn})"

    @property
    def finding(self):
        """What already exists in Nautobot."""
        if self.existing_authority is not None:
            return f"Already in Nautobot: CA certificate of {self.existing_authority}"
        if self.existing_certificate is not None:
            return "Certificate already in Nautobot (same SHA-256 fingerprint)"
        return "Not in Nautobot"

    @property
    def action_label(self):
        """Human readable proposed action."""
        if self.action == ACTION_CREATE_CA:
            certificate = "link the existing certificate" if self.existing_certificate else "create its certificate"
            return f"Create the Certificate Authority and {certificate}"
        if self.action == ACTION_LINK_CA:
            certificate = "the existing certificate" if self.existing_certificate else "the certificate (created)"
            return f"Link {certificate} to the existing CA {self.named_authority} (same name)"
        if self.action == ACTION_CREATE_CERTIFICATE:
            return "Create the certificate"
        return "None"


class BundlePlan:
    """Analysis of a PEM bundle: entries ordered from the top of the chain (issuers first)."""

    def __init__(self, parsed_certificates, user=None):
        """Analyze the parsed certificates of the bundle for `user` (permissions)."""
        self.user = user
        self.entries = [BundleEntry(index=index, parsed=parsed) for index, parsed in enumerate(parsed_certificates)]
        authority_certificates = load_authority_certificates()
        for entry in self.entries:
            self._find_existing(entry)
            self._find_issuer(entry, authority_certificates)
        for entry in self.entries:
            entry.depth = self._depth(entry)
        self.entries.sort(key=lambda entry: (entry.depth, entry.index))
        for entry in self.entries:
            self._propose_action(entry)
            self._check_permission(entry)

    @classmethod
    def from_pem(cls, pem_text, user=None):
        """Parse and analyze a PEM bundle. Raises `utils.CertificateParseError`."""
        return cls(utils.parse_pem_bundle(pem_text), user=user)

    @property
    def actionable_entries(self):
        """Entries with an action to confirm."""
        return [entry for entry in self.entries if entry.action != ACTION_NONE]

    @staticmethod
    def _find_existing(entry):
        fingerprint = entry.parsed.fingerprint_sha256
        entry.existing_certificate = models.Certificate.objects.filter(fingerprint_sha256=fingerprint).first()
        if entry.is_ca:
            entry.existing_authority = models.CertificateAuthority.objects.filter(
                certificate__fingerprint_sha256=fingerprint
            ).first()

    def _find_issuer(self, entry, authority_certificates):
        certificate = entry.parsed.certificate
        if utils.is_issued_by(certificate, certificate):
            entry.self_signed = True
            return
        issuers = [
            other
            for other in self.entries
            if other is not entry and other.is_ca and utils.is_issued_by(certificate, other.parsed.certificate)
        ]
        if len(issuers) == 1:
            entry.issuer_entry = issuers[0]
            return
        if len(issuers) > 1:
            entry.notes.append(
                "Several certificates of the bundle can have issued this certificate: issuer left empty."
            )
            return
        authorities = find_issuing_authorities(certificate, authority_certificates)
        if len(authorities) == 1:
            entry.issuer_authority = authorities[0]
        elif len(authorities) > 1:
            names = ", ".join(str(authority) for authority in authorities)
            entry.notes.append(
                f"Several Certificate Authorities can have issued this certificate ({names}): issuer left empty."
            )
        else:
            entry.notes.append("Issuer not found in the bundle nor in Nautobot: issuer left empty.")

    @staticmethod
    def _depth(entry):
        depth, current, seen = 0, entry, set()
        while current.issuer_entry is not None and current.index not in seen:
            seen.add(current.index)
            current = current.issuer_entry
            depth += 1
        return depth

    @staticmethod
    def _propose_action(entry):
        if not entry.is_ca:
            entry.action = ACTION_NONE if entry.existing_certificate else ACTION_CREATE_CERTIFICATE
            return
        if entry.existing_authority is not None:
            entry.action = ACTION_NONE
            return
        named = models.CertificateAuthority.objects.filter(name=default_authority_name(entry.parsed)).first()
        if named is None:
            entry.action = ACTION_CREATE_CA
        elif named.certificate_id is None:
            entry.named_authority = named
            entry.action = ACTION_LINK_CA
        else:
            entry.notes.append(
                f"The CA {named} already has another CA certificate: if this is a renewal, link it manually."
            )
            entry.action = ACTION_NONE if entry.existing_certificate else ACTION_CREATE_CERTIFICATE

    def _has_perm(self, permission):
        return self.user is None or self.user.has_perm(permission)

    def _check_permission(self, entry):
        missing = []
        if entry.creates_certificate and not self._has_perm("nautobot_ssl_manager.add_certificate"):
            missing.append("add certificates")
        if entry.action == ACTION_CREATE_CA and not self._has_perm("nautobot_ssl_manager.add_certificateauthority"):
            missing.append("add Certificate Authorities")
        if entry.action == ACTION_LINK_CA and not (
            self._has_perm("nautobot_ssl_manager.change_certificateauthority")
            and (
                self.user is None
                or models.CertificateAuthority.objects.restrict(self.user, "change")
                .filter(pk=entry.named_authority.pk)
                .exists()
            )
        ):
            missing.append(f"change the Certificate Authority {entry.named_authority}")
        if missing:
            entry.disabled_reason = f"You are not allowed to {' and '.join(missing)}."


class BundleImportError(Exception):
    """The confirmed actions could not be applied (nothing was saved)."""


def _issuing_authority(entry, authorities):
    """CA that issued the certificate of `entry`, as resolved after the previous entries were processed."""
    if entry.issuer_entry is not None:
        return authorities.get(entry.issuer_entry.index)
    return entry.issuer_authority


def _check_restricted(obj, user, action):
    if user is not None and not type(obj).objects.restrict(user, action).filter(pk=obj.pk).exists():
        raise BundleImportError(f"You are not allowed to {action} {obj}.")


def _create_certificate(entry, values, issuing_authority, user):
    parsed = entry.parsed
    certificate = models.Certificate(
        name=values["name"],
        common_name=parsed.common_name or values["name"],
        subject_alternative_names=parsed.subject_alternative_names,
        certificate_authority=issuing_authority,
        serial_number=parsed.serial_number,
        fingerprint_sha256=parsed.fingerprint_sha256,
        not_before=parsed.not_before,
        not_after=parsed.not_after,
        status=values["status"],
        key_algorithm=parsed.key_algorithm,
        key_size=parsed.key_size,
        validation_level=parsed.validation_level,
        extended_key_usage=parsed.extended_key_usage,
        pem=parsed.pem,
        tenant=values.get("tenant"),
    )
    certificate.validated_save()
    _check_restricted(certificate, user, "add")
    return certificate


def _apply_ca_entry(entry, values, issuing_authority, user):
    """Create or link the CA of a CA certificate entry, then create/link its certificate. Returns the CA."""
    parent = None if entry.self_signed else issuing_authority
    if entry.action == ACTION_CREATE_CA:
        authority = models.CertificateAuthority(
            name=values["ca_name"],
            type=values["ca_type"],
            status=values["ca_status"],
            provider=values.get("provider"),
            tenant=values.get("tenant"),
            parent=parent,
        )
        authority.validated_save()
        _check_restricted(authority, user, "add")
    else:
        authority = models.CertificateAuthority.objects.get(pk=entry.named_authority.pk)
        _check_restricted(authority, user, "change")
        if authority.parent_id is None and parent is not None:
            authority.parent = parent
    certificate = entry.existing_certificate
    if certificate is None:
        certificate = _create_certificate(entry, values, authority if entry.self_signed else issuing_authority, user)
    authority.certificate = certificate
    authority.validated_save()
    return authority, certificate


def _validation_messages(exc):
    if not hasattr(exc, "error_dict"):
        return exc.messages
    return [
        f"{'' if field_name == '__all__' else f'{field_name}: '}{error}"
        for field_name, errors in exc.message_dict.items()
        for error in errors
    ]


def _apply_entry(entry, values, authorities, user):
    """Apply the action of one entry. Returns the created or changed objects."""
    issuing_authority = _issuing_authority(entry, authorities)
    if entry.action in (ACTION_CREATE_CA, ACTION_LINK_CA):
        authority, certificate = _apply_ca_entry(entry, values, issuing_authority, user)
        authorities[entry.index] = authority
        return [authority] if entry.existing_certificate else [authority, certificate]
    return [_create_certificate(entry, values, issuing_authority, user)]


def apply_plan(plan, selections, user=None):
    """Apply the selected actions in a single transaction (issuers first).

    `selections` maps an entry index to the cleaned values of its row (only selected entries).
    Returns the list of created or changed objects. Raises `BundleImportError` (nothing is saved).
    """
    changed = []
    # CAs already linked to a certificate of the bundle can issue the next entries.
    authorities = {entry.index: entry.existing_authority for entry in plan.entries if entry.existing_authority}
    with transaction.atomic():
        for entry in plan.entries:
            values = selections.get(entry.index)
            if values is None or entry.action == ACTION_NONE or entry.disabled_reason:
                continue
            try:
                changed.extend(_apply_entry(entry, values, authorities, user))
            except ValidationError as exc:
                name = entry.parsed.common_name or entry.parsed.subject_dn
                raise BundleImportError(f"{name}: {' '.join(_validation_messages(exc))}") from exc
    return changed
