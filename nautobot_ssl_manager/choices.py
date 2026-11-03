"""Choice sets for Nautobot SSL Manager."""

from nautobot.apps.choices import ChoiceSet


class CertificateAuthorityTypeChoices(ChoiceSet):
    """Trust scope of a Certificate Authority."""

    TYPE_PUBLIC = "public"
    TYPE_PRIVATE = "private"

    CHOICES = (
        (TYPE_PUBLIC, "Public"),
        (TYPE_PRIVATE, "Private"),
    )


class KeyAlgorithmChoices(ChoiceSet):
    """Public key algorithm of a certificate."""

    RSA = "rsa"
    ECDSA = "ecdsa"
    ED25519 = "ed25519"

    CHOICES = (
        (RSA, "RSA"),
        (ECDSA, "ECDSA"),
        (ED25519, "Ed25519"),
    )


class ValidationLevelChoices(ChoiceSet):
    """Validation level of a certificate, as defined by the CA/Browser Forum certificate policies."""

    DV = "dv"
    OV = "ov"
    EV = "ev"

    CHOICES = (
        (DV, "Domain Validated (DV)"),
        (OV, "Organization Validated (OV)"),
        (EV, "Extended Validation (EV)"),
    )

    # CA/Browser Forum certificate policy OIDs
    POLICY_OIDS = {
        "2.23.140.1.2.1": DV,
        "2.23.140.1.2.2": OV,
        "2.23.140.1.1": EV,
    }


class ExtendedKeyUsageChoices(ChoiceSet):
    """Extended Key Usage purposes (RFC 5280, section 4.2.1.12)."""

    SERVER_AUTH = "serverAuth"
    CLIENT_AUTH = "clientAuth"
    CODE_SIGNING = "codeSigning"
    EMAIL_PROTECTION = "emailProtection"
    TIME_STAMPING = "timeStamping"
    OCSP_SIGNING = "OCSPSigning"

    CHOICES = (
        (SERVER_AUTH, "TLS Server Authentication"),
        (CLIENT_AUTH, "TLS Client Authentication"),
        (CODE_SIGNING, "Code Signing"),
        (EMAIL_PROTECTION, "Email Protection (S/MIME)"),
        (TIME_STAMPING, "Time Stamping"),
        (OCSP_SIGNING, "OCSP Signing"),
    )

    OIDS = {
        "1.3.6.1.5.5.7.3.1": SERVER_AUTH,
        "1.3.6.1.5.5.7.3.2": CLIENT_AUTH,
        "1.3.6.1.5.5.7.3.3": CODE_SIGNING,
        "1.3.6.1.5.5.7.3.4": EMAIL_PROTECTION,
        "1.3.6.1.5.5.7.3.8": TIME_STAMPING,
        "1.3.6.1.5.5.7.3.9": OCSP_SIGNING,
    }
