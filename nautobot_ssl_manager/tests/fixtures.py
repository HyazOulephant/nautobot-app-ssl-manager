"""Create fixtures for tests."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant, TenantGroup

from nautobot_ssl_manager.choices import (
    CertificateAuthorityTypeChoices,
    ExtendedKeyUsageChoices,
    KeyAlgorithmChoices,
    ValidationLevelChoices,
)
from nautobot_ssl_manager.models import Certificate, CertificateAuthority, CertificateProvider


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
    lab_root = CertificateAuthority.objects.create(
        name="Lab Root CA",
        type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        status=active,
    )
    # Chain: Lab Root CA (Root) -> Internal Issuing CA (Intermediate)
    CertificateAuthority.objects.filter(name="Internal Issuing CA").update(parent=lab_root)
    # Provider without any CA (needed for `has_certificate_authorities=False` filter tests)
    CertificateProvider.objects.create(name="Unused Provider", description="Provider without CA")


def get_certificate_statuses():
    """Return the statuses associated with Certificate (Planned, Active, Revoked, Retired)."""
    content_type = ContentType.objects.get_for_model(Certificate)
    return [
        Status.objects.get(name=name, content_types=content_type)
        for name in ("Planned", "Active", "Revoked", "Retired")
    ]


def create_certificates():
    """Create Certificate objects (and their CAs, providers and tenants) for tests."""
    create_certificate_authorities()
    tenant_one, tenant_two, tenant_three = create_tenants()
    planned, active, revoked, retired = get_certificate_statuses()
    sectigo_ca = CertificateAuthority.objects.get(name="Sectigo RSA Domain Validation")
    edge_ca = CertificateAuthority.objects.get(name="Google Trust Services WE1")
    internal_ca = CertificateAuthority.objects.get(name="Internal Issuing CA")
    now = timezone.now()

    old_www = Certificate.objects.create(
        name="www.example.com 2025",
        common_name="www.example.com",
        subject_alternative_names=["www.example.com", "example.com"],
        certificate_authority=sectigo_ca,
        serial_number="0a1b2c",
        fingerprint_sha256="a" * 64,
        not_before=now - timedelta(days=400),
        not_after=now - timedelta(days=35),
        status=retired,
        auto_renew=False,
        order_number="ORD-001",
        key_algorithm=KeyAlgorithmChoices.RSA,
        key_size=2048,
        validation_level=ValidationLevelChoices.DV,
        extended_key_usage=[ExtendedKeyUsageChoices.SERVER_AUTH],
        tenant=tenant_one,
        description="Old www certificate",
        comments="Expired",
    )
    Certificate.objects.create(
        name="www.example.com 2026",
        common_name="www.example.com",
        subject_alternative_names=["www.example.com", "example.com"],
        certificate_authority=sectigo_ca,
        serial_number="0d1e2f",
        fingerprint_sha256="b" * 64,
        not_before=now - timedelta(days=30),
        not_after=now + timedelta(days=335),
        status=active,
        replaces=old_www,
        auto_renew=True,
        order_number="ORD-002",
        key_algorithm=KeyAlgorithmChoices.RSA,
        key_size=4096,
        validation_level=ValidationLevelChoices.OV,
        extended_key_usage=[ExtendedKeyUsageChoices.SERVER_AUTH, ExtendedKeyUsageChoices.CLIENT_AUTH],
        tenant=tenant_one,
        description="Current www certificate",
    )
    Certificate.objects.create(
        name="Wildcard edge",
        common_name="*.edge.example.com",
        subject_alternative_names=["*.edge.example.com", "edge.example.com"],
        certificate_authority=edge_ca,
        serial_number="1a2b3c",
        fingerprint_sha256="c" * 64,
        not_after=now + timedelta(days=20),
        status=active,
        key_algorithm=KeyAlgorithmChoices.ECDSA,
        key_size=256,
        validation_level=ValidationLevelChoices.DV,
        extended_key_usage=[ExtendedKeyUsageChoices.SERVER_AUTH],
        tenant=tenant_two,
        description="Edge wildcard",
    )
    Certificate.objects.create(
        name="vpn-client-01",
        common_name="vpn-client-01.corp.example.com",
        subject_alternative_names=["vpn-client-01.corp.example.com", "10.0.0.1"],
        certificate_authority=internal_ca,
        not_after=now + timedelta(days=700),
        status=revoked,
        auto_renew=False,
        key_algorithm=KeyAlgorithmChoices.ED25519,
        extended_key_usage=[ExtendedKeyUsageChoices.CLIENT_AUTH],
        tenant=tenant_three,
    )
    Certificate.objects.create(
        name="Planned API certificate",
        common_name="api.example.com",
        not_after=now + timedelta(days=90),
        status=planned,
    )


def create_ca_certificate():
    """Create the certificate of the Lab Root CA and link it to that CA (needs `create_certificate_authorities()`)."""
    lab_root = CertificateAuthority.objects.get(name="Lab Root CA")
    certificate = Certificate.objects.create(
        name="Lab Root CA certificate",
        common_name="Lab Root CA",
        certificate_authority=lab_root,
        not_after=timezone.now() + timedelta(days=3650),
        status=get_certificate_statuses()[1],
    )
    lab_root.certificate = certificate
    lab_root.validated_save()
    return certificate
