"""Create fixtures for tests."""

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant, TenantGroup

from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.models import CertificateAuthority, CertificateProvider


def create_tenants():
    """Create tenant groups and tenants used by the fixtures (idempotent)."""
    group_one, _ = TenantGroup.objects.get_or_create(name="SSL Tenant Group One")
    group_two, _ = TenantGroup.objects.get_or_create(name="SSL Tenant Group Two")
    tenant_one, _ = Tenant.objects.get_or_create(name="SSL Tenant One", defaults={"tenant_group": group_one})
    tenant_two, _ = Tenant.objects.get_or_create(name="SSL Tenant Two", defaults={"tenant_group": group_two})
    tenant_three, _ = Tenant.objects.get_or_create(name="SSL Tenant Three", defaults={"tenant_group": group_two})
    return tenant_one, tenant_two, tenant_three


def get_certificate_authority_statuses():
    """Return the statuses associated with CertificateAuthority (Active, Deprecated, Retired)."""
    content_type = ContentType.objects.get_for_model(CertificateAuthority)
    return [Status.objects.get(name=name, content_types=content_type) for name in ("Active", "Deprecated", "Retired")]


def create_certificate_providers():
    """Create CertificateProvider objects for tests."""
    tenant_one, tenant_two, _ = create_tenants()
    CertificateProvider.objects.create(
        name="Sectigo",
        description="Sectigo description",
        portal_url="https://sectigo.example.com",
        tenant=tenant_one,
        comments="Sectigo comments",
    )
    CertificateProvider.objects.create(
        name="Cloudflare",
        description="Cloudflare description",
        portal_url="https://cloudflare.example.com",
        tenant=tenant_two,
        comments="Cloudflare comments",
    )
    CertificateProvider.objects.create(
        name="Internal",
        description="Internal description",
        portal_url="https://pki.example.com",
    )


def create_certificate_authorities():
    """Create CertificateAuthority objects (and their providers) for tests."""
    create_certificate_providers()
    tenant_one, tenant_two, tenant_three = create_tenants()
    active, deprecated, retired = get_certificate_authority_statuses()
    sectigo = CertificateProvider.objects.get(name="Sectigo")
    cloudflare = CertificateProvider.objects.get(name="Cloudflare")
    internal = CertificateProvider.objects.get(name="Internal")

    CertificateAuthority.objects.create(
        name="Sectigo RSA Domain Validation",
        type=CertificateAuthorityTypeChoices.TYPE_PUBLIC,
        status=active,
        provider=sectigo,
        description="Sectigo DV CA",
        portal_url="https://sectigo.example.com/dv",
        tenant=tenant_one,
        comments="First CA",
    )
    CertificateAuthority.objects.create(
        name="Google Trust Services WE1",
        type=CertificateAuthorityTypeChoices.TYPE_PUBLIC,
        status=deprecated,
        provider=cloudflare,
        description="Edge CA",
        portal_url="https://cloudflare.example.com/ca",
        tenant=tenant_two,
        comments="Second CA",
    )
    CertificateAuthority.objects.create(
        name="Internal Issuing CA",
        type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        status=retired,
        provider=internal,
        description="Internal issuing CA",
        portal_url="https://pki.example.com/issuing",
        tenant=tenant_three,
    )
    CertificateAuthority.objects.create(
        name="Lab Root CA",
        type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        status=active,
    )
    # Provider without any CA (needed for `has_certificate_authorities=False` filter tests)
    CertificateProvider.objects.create(name="Unused Provider", description="Provider without CA")
