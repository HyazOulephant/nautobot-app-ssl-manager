"""UI view tests for nautobot_ssl_manager."""

from nautobot.apps.testing import ViewTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import fixtures


class CertificateProviderViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the CertificateProvider views."""

    model = models.CertificateProvider

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificate_providers()
        tenant = fixtures.create_tenants()[0]
        cls.form_data = {
            "name": "View Provider",
            "description": "Created from view test",
            "portal_url": "https://view.example.com",
            "tenant": tenant.pk,
            "comments": "View comments",
        }
        cls.update_data = {
            "name": "View Provider Updated",
            "description": "Updated from view test",
        }
        cls.bulk_edit_data = {"description": "Bulk edit views"}


class CertificateAuthorityViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the CertificateAuthority views."""

    model = models.CertificateAuthority

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificate_authorities()
        active, deprecated, _ = fixtures.get_certificate_authority_statuses()
        provider = models.CertificateProvider.objects.get(name="Sectigo")
        cls.form_data = {
            "name": "View CA",
            "type": CertificateAuthorityTypeChoices.TYPE_PUBLIC,
            "status": active.pk,
            "provider": provider.pk,
            "description": "Created from view test",
            "portal_url": "https://view.example.com/ca",
            "comments": "View comments",
        }
        cls.update_data = {
            "name": "View CA Updated",
            "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            "status": deprecated.pk,
        }
        cls.bulk_edit_data = {
            "description": "Bulk edit views",
            "status": deprecated.pk,
            "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
        }
