"""Generate test data for the Nautobot SSL Manager app."""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from nautobot.extras.models import Status

from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.models import CertificateAuthority, CertificateProvider

PROVIDERS = (
    {"name": "Sectigo", "description": "Commercial certificate vendor", "portal_url": "https://www.sectigo.com"},
    {
        "name": "Let's Encrypt",
        "description": "Free ACME certificate authority",
        "portal_url": "https://letsencrypt.org",
    },
    {"name": "Internal PKI", "description": "Self-hosted PKI"},
)

# (name, type, status name, provider name)
CERTIFICATE_AUTHORITIES = (
    ("Sample Sectigo DV CA", CertificateAuthorityTypeChoices.TYPE_PUBLIC, "Active", "Sectigo"),
    ("Sample Let's Encrypt CA", CertificateAuthorityTypeChoices.TYPE_PUBLIC, "Active", "Let's Encrypt"),
    ("Sample Internal Root CA", CertificateAuthorityTypeChoices.TYPE_PRIVATE, "Active", "Internal PKI"),
    ("Sample Legacy Internal CA", CertificateAuthorityTypeChoices.TYPE_PRIVATE, "Deprecated", "Internal PKI"),
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

    def _generate_static_data(self, db):
        """Generate static data required for test cases."""
        content_type = ContentType.objects.db_manager(db).get_for_model(CertificateAuthority)
        for provider_data in PROVIDERS:
            CertificateProvider.objects.using(db).get_or_create(
                name=provider_data["name"], defaults={k: v for k, v in provider_data.items() if k != "name"}
            )
        for name, ca_type, status_name, provider_name in CERTIFICATE_AUTHORITIES:
            CertificateAuthority.objects.using(db).get_or_create(
                name=name,
                defaults={
                    "type": ca_type,
                    "status": Status.objects.using(db).get(name=status_name, content_types=content_type),
                    "provider": CertificateProvider.objects.using(db).get(name=provider_name),
                },
            )

    def handle(self, *args, **options):
        """Entry point to the management command."""
        db = options["database"]
        if options["flush"]:
            self.stdout.write("Flushing existing Nautobot SSL Manager test data...")
            CertificateAuthority.objects.using(db).filter(name__in=[ca[0] for ca in CERTIFICATE_AUTHORITIES]).delete()
            CertificateProvider.objects.using(db).filter(name__in=[p["name"] for p in PROVIDERS]).delete()

        self._generate_static_data(db=db)

        self.stdout.write(self.style.SUCCESS(f"Database {db} populated with app data successfully!"))
