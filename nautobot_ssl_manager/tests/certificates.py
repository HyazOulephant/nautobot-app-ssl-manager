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
):
    """Build a self-issued certificate and return `(pem, certificate, private_key)`."""
    private_key = _private_key(key_type)
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
    algorithm = None if key_type == "ed25519" else hashes.SHA256()
    certificate = builder.sign(private_key, algorithm)
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
