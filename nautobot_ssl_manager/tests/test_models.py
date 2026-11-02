"""Test models for nautobot_ssl_manager."""

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from nautobot.apps.testing import ModelTestCases
from nautobot.extras.models import Status

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import fixtures


class TestCertificateProvider(ModelTestCases.BaseModelTestCase):
    """Test CertificateProvider."""

    model = models.CertificateProvider

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificate_providers()

    def test_create_only_required(self):
        """Create with only required fields."""
        provider = models.CertificateProvider.objects.create(name="Let's Encrypt")
        self.assertEqual(provider.name, "Let's Encrypt")
        self.assertEqual(provider.description, "")
        self.assertEqual(provider.portal_url, "")
        self.assertIsNone(provider.tenant)
        self.assertEqual(provider.comments, "")
        self.assertEqual(str(provider), "Let's Encrypt")

    def test_name_is_unique(self):
        """Two providers cannot share the same name."""
        with self.assertRaises(IntegrityError):
            models.CertificateProvider.objects.create(name="Sectigo")

    def test_delete_protected_when_used_by_ca(self):
        """A provider referenced by a CA cannot be deleted."""
        provider = models.CertificateProvider.objects.get(name="Sectigo")
        models.CertificateAuthority.objects.create(
            name="Protected CA",
            type=CertificateAuthorityTypeChoices.TYPE_PUBLIC,
            status=fixtures.get_certificate_authority_statuses()[0],
            provider=provider,
        )
        with self.assertRaises(ProtectedError):
            provider.delete()


class TestCertificateAuthority(ModelTestCases.BaseModelTestCase):
    """Test CertificateAuthority."""

    model = models.CertificateAuthority

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificate_authorities()

    def test_create_only_required(self):
        """Create with only required fields."""
        active = fixtures.get_certificate_authority_statuses()[0]
        ca = models.CertificateAuthority.objects.create(
            name="Minimal CA",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=active,
        )
        self.assertEqual(ca.name, "Minimal CA")
        self.assertEqual(ca.type, CertificateAuthorityTypeChoices.TYPE_PRIVATE)
        self.assertEqual(ca.status, active)
        self.assertIsNone(ca.provider)
        self.assertIsNone(ca.tenant)
        self.assertEqual(str(ca), "Minimal CA")

    def test_name_is_unique(self):
        """Two CAs cannot share the same name."""
        with self.assertRaises(IntegrityError):
            models.CertificateAuthority.objects.create(
                name="Lab Root CA",
                type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
                status=fixtures.get_certificate_authority_statuses()[0],
            )

    def test_default_statuses_available(self):
        """Active, Deprecated and Retired statuses are associated with the model by migration."""
        content_type = ContentType.objects.get_for_model(models.CertificateAuthority)
        names = set(Status.objects.filter(content_types=content_type).values_list("name", flat=True))
        self.assertTrue({"Active", "Deprecated", "Retired"}.issubset(names))

    def test_provider_reverse_relation(self):
        """Provider exposes its CAs through `certificate_authorities`."""
        provider = models.CertificateProvider.objects.get(name="Sectigo")
        self.assertEqual(
            list(provider.certificate_authorities.values_list("name", flat=True)),
            ["Sectigo RSA Domain Validation"],
        )
