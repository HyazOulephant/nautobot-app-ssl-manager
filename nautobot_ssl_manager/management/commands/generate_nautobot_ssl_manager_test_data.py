"""Generate test data for the Nautobot SSL Manager app."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.utils import timezone
from nautobot.extras.models import Status

from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices, ExtendedKeyUsageChoices
from nautobot_ssl_manager.models import Certificate, CertificateAuthority, CertificateProvider

PROVIDERS = (
    {"name": "Sectigo", "description": "Commercial certificate vendor", "portal_url": "https://www.sectigo.com"},
    {
        "name": "Let's Encrypt",
        "description": "Free ACME certificate authority",
        "portal_url": "https://letsencrypt.org",
    },
    {"name": "Internal PKI", "description": "Self-hosted PKI"},
)

# (name, type, status name, provider name, issuer CA name) - issuers are listed before the CAs they issued.
CERTIFICATE_AUTHORITIES = (
    ("Sample Sectigo Root CA", CertificateAuthorityTypeChoices.TYPE_PUBLIC, "Active", "Sectigo", None),
    (
        "Sample Sectigo DV CA",
        CertificateAuthorityTypeChoices.TYPE_PUBLIC,
        "Active",
        "Sectigo",
        "Sample Sectigo Root CA",
    ),
    ("Sample Let's Encrypt CA", CertificateAuthorityTypeChoices.TYPE_PUBLIC, "Active", "Let's Encrypt", None),
    ("Sample Internal Root CA", CertificateAuthorityTypeChoices.TYPE_PRIVATE, "Active", "Internal PKI", None),
    (
        "Sample Internal Issuing CA",
        CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        "Active",
        "Internal PKI",
        "Sample Internal Root CA",
    ),
    (
        "Sample Legacy Internal CA",
        CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        "Deprecated",
        "Internal PKI",
        "Sample Internal Root CA",
    ),
)

# (name, common name, SANs, CA name, status name, days before expiration, EKU)
CERTIFICATES = (
    (
        "Sample www.example.com",
        "www.example.com",
        ["www.example.com", "example.com"],
        "Sample Sectigo DV CA",
        "Active",
        200,
        [ExtendedKeyUsageChoices.SERVER_AUTH],
    ),
    (
        "Sample wildcard example.net",
        "*.example.net",
        ["*.example.net", "example.net"],
        "Sample Let's Encrypt CA",
        "Active",
        15,
        [ExtendedKeyUsageChoices.SERVER_AUTH],
    ),
    (
        "Sample VPN client",
        "vpn-client.corp.example.com",
        ["vpn-client.corp.example.com"],
        "Sample Internal Issuing CA",
        "Active",
        -3,
        [ExtendedKeyUsageChoices.CLIENT_AUTH],
    ),
)


class Command(BaseCommand):
    """Populate the database with various data as a baseline for testing (automated or manual)."""

    help = __doc__

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to generate the test data in. Defaults to the "default" database.',
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush any existing Nautobot SSL Manager test data from the database before generating new data.",
        )

    @staticmethod
    def _generate_certificate_authorities(db, content_type):
        """Generate the CAs, issuers first."""
        for name, ca_type, status_name, provider_name, parent_name in CERTIFICATE_AUTHORITIES:
            CertificateAuthority.objects.using(db).get_or_create(
                name=name,
                defaults={
                    "type": ca_type,
                    "status": Status.objects.using(db).get(name=status_name, content_types=content_type),
                    "provider": CertificateProvider.objects.using(db).get(name=provider_name),
                    "parent": CertificateAuthority.objects.using(db).get(name=parent_name) if parent_name else None,
                },
            )

    def _generate_static_data(self, db):
        """Generate static data required for test cases."""
        content_type = ContentType.objects.db_manager(db).get_for_model(CertificateAuthority)
        for provider_data in PROVIDERS:
            CertificateProvider.objects.using(db).get_or_create(
                name=provider_data["name"], defaults={k: v for k, v in provider_data.items() if k != "name"}
            )
        self._generate_certificate_authorities(db, content_type)

        certificate_content_type = ContentType.objects.db_manager(db).get_for_model(Certificate)
        now = timezone.now()
        for name, common_name, sans, ca_name, status_name, days, eku in CERTIFICATES:
            Certificate.objects.using(db).get_or_create(
                name=name,
                defaults={
                    "common_name": common_name,
                    "subject_alternative_names": sans,
                    "certificate_authority": CertificateAuthority.objects.using(db).get(name=ca_name),
                    "status": Status.objects.using(db).get(name=status_name, content_types=certificate_content_type),
                    "not_before": now - timedelta(days=90),
                    "not_after": now + timedelta(days=days),
                    "extended_key_usage": eku,
                },
            )

    def handle(self, *args, **options):
        """Entry point to the management command."""
        db = options["database"]
        if options["flush"]:
            self.stdout.write("Flushing existing Nautobot SSL Manager test data...")
            Certificate.objects.using(db).filter(name__in=[certificate[0] for certificate in CERTIFICATES]).delete()
            # Issued CAs first: a CA cannot be deleted while it still has issued CAs.
            for ca in reversed(CERTIFICATE_AUTHORITIES):
                CertificateAuthority.objects.using(db).filter(name=ca[0]).delete()
            CertificateProvider.objects.using(db).filter(name__in=[p["name"] for p in PROVIDERS]).delete()

        self._generate_static_data(db=db)

        self.stdout.write(self.style.SUCCESS(f"Database {db} populated with app data successfully!"))
