"""Models for Nautobot SSL Manager."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import PrimaryModel, StatusField, TreeModel, extras_features
from tree_queries.fields import TreeNodeForeignKey

from nautobot_ssl_manager import utils
from nautobot_ssl_manager.choices import (
    CertificateAuthorityTypeChoices,
    ExtendedKeyUsageChoices,
    KeyAlgorithmChoices,
    ValidationLevelChoices,
)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CertificateProvider(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Vendor or service through which certificates are obtained (e.g. Sectigo, Cloudflare)."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    portal_url = models.URLField(blank=True, verbose_name="Portal URL")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="certificate_providers",
        blank=True,
        null=True,
    )
    comments = models.TextField(blank=True)

    class Meta:
        """Meta class."""

        ordering = ["name"]
        verbose_name = "Certificate Provider"
        verbose_name_plural = "Certificate Providers"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class CertificateAuthority(TreeModel, PrimaryModel):  # pylint: disable=too-many-ancestors
    """Certificate Authority (CA) issuing SSL/TLS certificates.

    CAs form a tree through `parent` (the CA that issued this CA's certificate): a CA without parent is a Root CA,
    a CA with a parent is an Intermediate CA.
    """

    ROLE_ROOT = "Root"
    ROLE_INTERMEDIATE = "Intermediate"

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    parent = TreeNodeForeignKey(
        to="self",
        on_delete=models.PROTECT,
        related_name="children",
        blank=True,
        null=True,
        verbose_name="Issued by",
        help_text="CA that issued this CA's certificate. Leave empty for a Root CA.",
    )
    type = models.CharField(
        max_length=50,
        choices=CertificateAuthorityTypeChoices,
        help_text="Public (publicly trusted) or Private (internal / non publicly trusted) CA",
    )
    status = StatusField(blank=False, null=False)
    provider = models.ForeignKey(
        to="nautobot_ssl_manager.CertificateProvider",
        on_delete=models.PROTECT,
        related_name="certificate_authorities",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    portal_url = models.URLField(blank=True, verbose_name="Portal URL")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="certificate_authorities",
        blank=True,
        null=True,
    )
    comments = models.TextField(blank=True)
    certificate = models.OneToOneField(
        to="nautobot_ssl_manager.Certificate",
        on_delete=models.SET_NULL,
        related_name="ca_certificate_of",
        blank=True,
        null=True,
        verbose_name="CA certificate",
        help_text="Certificate of this CA (its own certificate, not a certificate it issued)",
    )

    clone_fields = ["parent", "type", "status", "provider", "tenant"]

    class Meta:
        """Meta class."""

        ordering = ["name"]
        verbose_name = "Certificate Authority"
        verbose_name_plural = "Certificate Authorities"

    def __str__(self):
        """Stringify instance."""
        return self.name

    @property
    def chain_role(self):
        """Role deduced from the tree: Root without parent, Intermediate otherwise."""
        return self.ROLE_INTERMEDIATE if self.parent_id else self.ROLE_ROOT

    @property
    def chain(self):
        """This CA followed by its issuers, up to the Root CA."""
        return list(self.ancestors(include_self=True))[::-1]

    def clean(self):
        """Validate the consistency of the CA certificate with this CA."""
        super().clean()
        if self.certificate_id:
            messages = [message for _, message in ca_certificate_inconsistencies(self, self.certificate)]
            if messages:
                raise ValidationError({"certificate": messages})


def _parse_stored_pem(certificate):
    """Parse the PEM stored on a Certificate, or None if absent or invalid (reported by `Certificate.clean()`)."""
    if certificate is None or not certificate.pem:
        return None
    try:
        return utils.parse_pem_certificate(certificate.pem)
    except utils.CertificateParseError:
        return None


def ca_certificate_inconsistencies(authority, certificate):
    """Return the facts proving that `certificate` cannot be the certificate of `authority`.

    Only certain facts are checked (data stored in Nautobot or read from the PEMs); nothing is guessed.
    Each entry is `(kind, message)`, `kind` being "pem" (content of the certificate itself) or
    "issuer" (consistency with the CA tree).
    """
    errors = []
    parsed = _parse_stored_pem(certificate)
    if parsed is not None and not parsed.is_ca:
        errors.append(("pem", "This certificate is not a CA certificate (basicConstraints CA:TRUE is missing)."))

    # The CA certificate is issued by the parent CA, or by the CA itself (self-signed Root CA).
    if certificate.certificate_authority_id:
        expected_issuer_id = authority.parent_id or authority.pk
        if certificate.certificate_authority_id != expected_issuer_id:
            expected = authority.parent if authority.parent_id else "the CA itself (Root CA)"
            errors.append(
                (
                    "issuer",
                    f"The certificate is issued by {certificate.certificate_authority}, "
                    f"but the CA is issued by {expected}.",
                )
            )

    # When both PEMs are known, the certificate issuer must be the subject of the parent CA certificate.
    if parsed is not None and authority.parent_id:
        parent_parsed = _parse_stored_pem(authority.parent.certificate)
        if parent_parsed is not None and parsed.issuer_dn != parent_parsed.subject_dn:
            errors.append(
                (
                    "issuer",
                    f"The certificate issuer ({parsed.issuer_dn}) does not match the subject of the certificate "
                    f"of {authority.parent} ({parent_parsed.subject_dn}).",
                )
            )
    return errors


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Certificate(PrimaryModel):  # pylint: disable=too-many-ancestors
    """SSL/TLS certificate (public part only: private keys are never stored)."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    common_name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, verbose_name="Common Name")
    subject_alternative_names = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Subject Alternative Names",
        help_text="DNS names and IP addresses; other types are prefixed with 'email:' or 'uri:'",
    )
    certificate_authority = models.ForeignKey(
        to="nautobot_ssl_manager.CertificateAuthority",
        on_delete=models.PROTECT,
        related_name="certificates",
        blank=True,
        null=True,
        verbose_name="Certificate Authority",
    )
    serial_number = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    # Unique only when set (same pattern as Nautobot core `Device.asset_tag`), hence null=True on a CharField.
    fingerprint_sha256 = models.CharField(  # pylint: disable=nb-string-field-blank-null
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        verbose_name="SHA-256 Fingerprint",
    )
    not_before = models.DateTimeField(blank=True, null=True, verbose_name="Valid from")
    not_after = models.DateTimeField(verbose_name="Expires")
    status = StatusField(blank=False, null=False)
    replaces = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        related_name="replaced_by",
        blank=True,
        null=True,
        help_text="Previous certificate replaced by this one (renewal)",
    )
    auto_renew = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Auto-renew",
        help_text="Leave empty if unknown",
    )
    order_number = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    key_algorithm = models.CharField(max_length=50, choices=KeyAlgorithmChoices, blank=True)
    key_size = models.PositiveIntegerField(blank=True, null=True)
    validation_level = models.CharField(max_length=50, choices=ValidationLevelChoices, blank=True)
    extended_key_usage = models.JSONField(default=list, blank=True, verbose_name="Extended Key Usage")
    pem = models.TextField(blank=True, verbose_name="PEM", help_text="Public certificate only")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="certificates",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    comments = models.TextField(blank=True)

    clone_fields = ["certificate_authority", "status", "tenant", "auto_renew", "key_algorithm", "key_size"]

    # No mandatory unique business field (the fingerprint is optional): use the primary key as natural key.
    natural_key_field_names = ["pk"]

    class Meta:
        """Meta class."""

        ordering = ["not_after", "name"]
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"

    def __str__(self):
        """Stringify instance."""
        return self.name

    #
    # Computed properties
    #

    @property
    def days_remaining(self):
        """Number of full days before expiration (negative once expired)."""
        if self.not_after is None:
            return None
        return (self.not_after - timezone.now()).days

    @property
    def is_expired(self):
        """True if the certificate is past its expiration date."""
        if self.not_after is None:
            return None
        return self.not_after <= timezone.now()

    @property
    def chain(self):
        """Issuing CA followed by its issuers, up to the Root CA (empty when no CA is set)."""
        if not self.certificate_authority_id:
            return []
        return self.certificate_authority.chain

    @property
    def ca_certificate_authority(self):
        """Certificate Authority whose own certificate is this one (None for a certificate not linked to a CA)."""
        if not self.present_in_database:
            return None
        try:
            return self.ca_certificate_of  # pylint: disable=no-member
        except ObjectDoesNotExist:
            return None

    @property
    def is_wildcard(self):
        """True if at least one SAN (or the CN) is a wildcard DNS name."""
        names = [self.common_name, *(self.subject_alternative_names or [])]
        return any(utils.is_wildcard_san(name) for name in names if name)

    def get_extended_key_usage_display(self):
        """Human readable labels of the Extended Key Usage values."""
        labels = dict(ExtendedKeyUsageChoices.CHOICES)
        return [labels.get(value, value) for value in self.extended_key_usage or []]

    #
    # Validation
    #

    def _normalize(self):
        """Normalize identifiers and lists (safe to call several times)."""
        self.serial_number = utils.normalize_hex(self.serial_number) or ""
        self.fingerprint_sha256 = utils.normalize_hex(self.fingerprint_sha256) or None
        if self.subject_alternative_names is None:
            self.subject_alternative_names = []
        if isinstance(self.subject_alternative_names, list):
            try:
                self.subject_alternative_names = utils.normalize_san_list(self.subject_alternative_names)
            except ValueError:
                pass  # Reported by clean()
        if self.extended_key_usage is None:
            self.extended_key_usage = []
        if self.pem:
            try:
                self.pem = utils.parse_pem_certificate(self.pem).pem
            except utils.CertificateParseError:
                pass  # Reported by clean()

    def clean_fields(self, exclude=None):
        """Normalize values before Django's field validation (e.g. max_length of the fingerprint)."""
        self._normalize()
        super().clean_fields(exclude=exclude)

    def _validate_lists(self, errors):
        """Validate the SAN and Extended Key Usage lists."""
        if not isinstance(self.subject_alternative_names, list):
            errors["subject_alternative_names"] = "Must be a list."
        else:
            try:
                self.subject_alternative_names = utils.normalize_san_list(self.subject_alternative_names)
            except ValueError as exc:
                errors["subject_alternative_names"] = str(exc)

        valid_eku = set(ExtendedKeyUsageChoices.values())
        if not isinstance(self.extended_key_usage, list):
            errors["extended_key_usage"] = "Must be a list."
        elif invalid := [value for value in self.extended_key_usage if value not in valid_eku]:
            errors["extended_key_usage"] = f"Invalid value(s): {', '.join(map(str, invalid))}."

    def _validate_identifiers(self, errors):
        """Validate the serial number and the fingerprint format."""
        if self.serial_number and not utils.is_hex(self.serial_number):
            errors["serial_number"] = "Must be a hexadecimal value."
        if self.fingerprint_sha256 and (
            len(self.fingerprint_sha256) != 64 or not utils.is_hex(self.fingerprint_sha256)
        ):
            errors["fingerprint_sha256"] = "Must be a SHA-256 fingerprint (64 hexadecimal characters)."

    def _validate_pem(self, errors):
        """Validate the PEM (public certificate only) and its consistency with the fingerprint."""
        if not self.pem:
            return
        try:
            parsed = utils.parse_pem_certificate(self.pem)
        except utils.CertificateParseError as exc:
            errors["pem"] = str(exc)
            return
        self.pem = parsed.pem
        if self.fingerprint_sha256 and self.fingerprint_sha256 != parsed.fingerprint_sha256:
            errors["fingerprint_sha256"] = "Does not match the fingerprint of the PEM certificate."

    def clean(self):
        """Validate the certificate data."""
        super().clean()
        self._normalize()
        errors = {}
        self._validate_lists(errors)
        self._validate_identifiers(errors)
        if self.not_before and self.not_after and self.not_before > self.not_after:
            errors["not_after"] = "Expiration must be after the 'Valid from' date."
        if self.replaces_id and self.pk and self.replaces_id == self.pk:
            errors["replaces"] = "A certificate cannot replace itself."
        self._validate_pem(errors)
        if "pem" not in errors and (authority := self.ca_certificate_authority) is not None:
            fields = {"pem": "pem", "issuer": "certificate_authority"}
            for kind, message in ca_certificate_inconsistencies(authority, self):
                errors.setdefault(fields[kind], []).append(message)
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Normalize data before saving."""
        self._normalize()
        super().save(*args, **kwargs)
