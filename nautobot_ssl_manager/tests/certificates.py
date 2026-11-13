"""Generate throw-away X.509 certificates for tests (never use these helpers outside tests)."""

import ipaddress
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

DV_POLICY = "2.23.140.1.2.1"
OV_POLICY = "2.23.140.1.2.2"
EV_POLICY = "2.23.140.1.1"


def _private_key(key_type):
    if key_type == "rsa":
        return rsa.generate_private_key(public_exponent=65537, key_size=2048)
    if key_type == "ec":
        return ec.generate_private_key(ec.SECP256R1())
    if key_type == "ed25519":
        return ed25519.Ed25519PrivateKey.generate()
    raise ValueError(key_type)


def build_certificate(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    common_name="www.example.com",
    dns_names=("www.example.com", "example.com"),
    ip_addresses=(),
    emails=(),
    uris=(),
    eku=(ExtendedKeyUsageOID.SERVER_AUTH,),
    policies=(),
    key_type="rsa",
    is_ca=False,
    issuer_common_name="Test Issuing CA",
    days=90,
    issuer_key=None,
    key_identifiers=False,
    private_key=None,
):
    """Build a certificate and return `(pem, certificate, private_key)`.

    Signed with its own key (self-issued, the issuer name being only a label), or with `issuer_key` to build a real
    chain whose signatures can be verified.
    """
    private_key = private_key or _private_key(key_type)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]) if common_name else x509.Name([])
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
    )
    general_names = [
        *(x509.DNSName(name) for name in dns_names),
        *(x509.IPAddress(ipaddress.ip_address(ip)) for ip in ip_addresses),
        *(x509.RFC822Name(email) for email in emails),
        *(x509.UniformResourceIdentifier(uri) for uri in uris),
    ]
    if general_names:
        builder = builder.add_extension(x509.SubjectAlternativeName(general_names), critical=False)
    if eku:
        builder = builder.add_extension(x509.ExtendedKeyUsage(list(eku)), critical=False)
    if policies:
        builder = builder.add_extension(
            x509.CertificatePolicies([x509.PolicyInformation(x509.ObjectIdentifier(oid), None) for oid in policies]),
            critical=False,
        )
    if key_identifiers:
        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key((issuer_key or private_key).public_key()), critical=False
        )
    signing_key = issuer_key or private_key
    algorithm = None if isinstance(signing_key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
    certificate = builder.sign(signing_key, algorithm)
    pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return pem, certificate, private_key


def private_key_pem(private_key):
    """Serialize a private key to PEM (used to test that private keys are rejected)."""
    return private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()


def fingerprint(certificate):
    """SHA-256 fingerprint as stored by the app (lowercase hex, no separators)."""
    return certificate.fingerprint(hashes.SHA256()).hex()


def build_chain(
    root="Bundle Root CA", intermediate="Bundle Issuing CA", leaf="www.bundle.example.com", key_identifiers=False
):
    """Build a real chain (signatures verifiable): Root CA -> Intermediate CA -> leaf. Returns the 3 PEMs."""
    common = {"key_identifiers": key_identifiers}
    root_pem, _, root_key = build_certificate(
        common_name=root, issuer_common_name=root, is_ca=True, dns_names=(), eku=(), **common
    )
    intermediate_pem, _, intermediate_key = build_certificate(
        common_name=intermediate,
        issuer_common_name=root,
        is_ca=True,
        dns_names=(),
        eku=(),
        issuer_key=root_key,
        **common,
    )
    leaf_pem = build_certificate(
        common_name=leaf, dns_names=(leaf,), issuer_common_name=intermediate, issuer_key=intermediate_key, **common
    )[0]
    return root_pem, intermediate_pem, leaf_pem
