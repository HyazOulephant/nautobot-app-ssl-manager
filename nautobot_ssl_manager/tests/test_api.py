"""API tests for nautobot_ssl_manager."""

from nautobot.apps.testing import APIViewTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import fixtures


class CertificateProviderAPIViewTest(APIViewTestCases.APIViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the API viewsets for CertificateProvider."""

    model = models.CertificateProvider
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificate_providers()
        tenant = fixtures.create_tenants()[0]
        cls.create_data = [
            {"name": "API Provider One", "description": "One", "portal_url": "https://one.example.com"},
            {"name": "API Provider Two", "tenant": tenant.pk},
            {"name": "API Provider Three", "comments": "Three"},
        ]
        cls.update_data = {"name": "API Provider Updated", "description": "Updated"}
        cls.bulk_update_data = {"description": "Bulk updated"}


class CertificateAuthorityAPIViewTest(APIViewTestCases.APIViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the API viewsets for CertificateAuthority."""

    model = models.CertificateAuthority
    choices_fields = ("type",)

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificate_authorities()
        active, deprecated, _ = fixtures.get_certificate_authority_statuses()
        provider = models.CertificateProvider.objects.get(name="Sectigo")
        tenant = fixtures.create_tenants()[0]
        cls.create_data = [
            {
                "name": "API CA One",
                "type": CertificateAuthorityTypeChoices.TYPE_PUBLIC,
                "status": active.pk,
                "provider": provider.pk,
            },
            {
                "name": "API CA Two",
                "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
                "status": deprecated.pk,
                "tenant": tenant.pk,
            },
            {
                "name": "API CA Three",
                "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
                "status": active.pk,
                "portal_url": "https://three.example.com",
            },
        ]
        cls.update_data = {"name": "API CA Updated", "status": deprecated.pk}
        cls.bulk_update_data = {"description": "Bulk updated"}
