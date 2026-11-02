"""Models for Nautobot SSL Manager."""

from django.db import models
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import PrimaryModel, StatusField, extras_features

from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices


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
class CertificateAuthority(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Certificate Authority (CA) issuing SSL/TLS certificates."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
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

    clone_fields = ["type", "status", "provider", "tenant"]

    class Meta:
        """Meta class."""

        ordering = ["name"]
        verbose_name = "Certificate Authority"
        verbose_name_plural = "Certificate Authorities"

    def __str__(self):
        """Stringify instance."""
        return self.name
