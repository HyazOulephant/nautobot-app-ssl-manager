"""Identification of the Certificate Authority that issued a certificate.

The issuer is **proven** by signature verification with the CA certificates stored in Nautobot (CA certificate link):

- candidates are pre-selected with the key identifiers (Authority Key Identifier of the certificate = Subject Key
  Identifier of the CA certificate) when both extensions are present; otherwise every stored CA certificate is a
  candidate, `cryptography` checking that the issuer name matches its subject;
- a candidate is retained only if the certificate signature is verified with its public key.

When nothing can be proven, a CA named exactly like the issuer Common Name is only a suggestion.
"""

from dataclasses import dataclass, field

from cryptography import x509

from nautobot_ssl_manager import models, utils

METHOD_SIGNATURE = "signature"
METHOD_AMBIGUOUS = "ambiguous"
METHOD_NAME = "name"


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


def find_issuing_authorities(certificate, authorities_with_certificate=None):
    """Certificate Authorities whose stored CA certificate is proven to have issued `certificate` (x509).

    `authorities_with_certificate` is an optional list of `(CertificateAuthority, x509.Certificate)` to avoid loading
    the CA certificates several times.
    """
    if authorities_with_certificate is None:
        authorities_with_certificate = load_authority_certificates()
    authority_key_id = utils.authority_key_identifier(certificate)
    issuers = []
    for authority, ca_certificate in authorities_with_certificate:
        if authority in issuers:
            continue
        subject_key_id = utils.subject_key_identifier(ca_certificate)
        if authority_key_id and subject_key_id and authority_key_id != subject_key_id:
            continue
        if utils.is_issued_by(certificate, ca_certificate):
            issuers.append(authority)
    return issuers


@dataclass
class IssuerIdentification:
    """How the issuing CA of a certificate was found.

    `method` is `signature` (exactly one CA proven), `ambiguous` (several CAs proven), `name` (no CA proven, CA named
    like the issuer Common Name, not verified) or None (nothing found).
    """

    method: str = None
    authorities: list = field(default_factory=list)

    @property
    def proven_authority(self):
        """The CA to pre-select: only when exactly one CA is proven by signature."""
        return self.authorities[0] if self.method == METHOD_SIGNATURE else None

    def to_session(self):
        """JSON serializable form (stored with the pending PEM import)."""
        return {"method": self.method, "authorities": [str(authority.pk) for authority in self.authorities]}


def identify_issuer(parsed, authorities_with_certificate=None):
    """Identify the issuing CA of a `utils.ParsedCertificate`."""
    proven = find_issuing_authorities(parsed.certificate, authorities_with_certificate)
    if len(proven) == 1:
        return IssuerIdentification(METHOD_SIGNATURE, proven)
    if len(proven) > 1:
        return IssuerIdentification(METHOD_AMBIGUOUS, proven)
    if parsed.issuer_common_name:
        named = models.CertificateAuthority.objects.filter(name=parsed.issuer_common_name).first()
        if named is not None:
            return IssuerIdentification(METHOD_NAME, [named])
    return IssuerIdentification()
