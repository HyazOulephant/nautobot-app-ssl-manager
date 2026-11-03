"""Test models for nautobot_ssl_manager."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from nautobot.apps.testing import ModelTestCases
from nautobot.extras.models import Status

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures


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

    def test_chain_role_deduced_from_tree(self):
        """A CA without issuer is a Root CA, a CA with an issuer is an Intermediate CA."""
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        intermediate = models.CertificateAuthority.objects.get(name="Internal Issuing CA")
        self.assertEqual(root.chain_role, models.CertificateAuthority.ROLE_ROOT)
        self.assertEqual(intermediate.chain_role, models.CertificateAuthority.ROLE_INTERMEDIATE)

    def test_chain(self):
        """The chain goes from the CA up to the Root CA."""
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        intermediate = models.CertificateAuthority.objects.get(name="Internal Issuing CA")
        sub = models.CertificateAuthority.objects.create(
            name="Lab Sub CA",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=root.status,
            parent=intermediate,
        )
        self.assertEqual(sub.chain, [sub, intermediate, root])
        self.assertEqual(root.chain, [root])
        self.assertEqual(list(root.children.all()), [intermediate])

    def test_cannot_be_issued_by_itself_or_a_descendant(self):
        """Loops in the chain are rejected."""
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        intermediate = models.CertificateAuthority.objects.get(name="Internal Issuing CA")
        root.parent = root
        with self.assertRaises(ValidationError):
            root.validated_save()
        root.parent = intermediate
        with self.assertRaises(ValidationError):
            root.validated_save()

    def test_issuer_delete_protected(self):
        """A CA cannot be deleted while it still has issued CAs."""
        with self.assertRaises(ProtectedError):
            models.CertificateAuthority.objects.get(name="Lab Root CA").delete()


class TestCertificate(ModelTestCases.BaseModelTestCase):
    """Test Certificate."""

    model = models.Certificate

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificates()

    def setUp(self):
        self.active = fixtures.get_certificate_statuses()[1]

    def _build(self, **kwargs):
        data = {
            "name": "Test certificate",
            "common_name": "test.example.com",
            "not_after": timezone.now() + timedelta(days=30),
            "status": self.active,
        }
        data.update(kwargs)
        return models.Certificate(**data)

    def test_create_only_required(self):
        certificate = self._build()
        certificate.validated_save()
        self.assertEqual(certificate.subject_alternative_names, [])
        self.assertEqual(certificate.extended_key_usage, [])
        self.assertIsNone(certificate.auto_renew)
        self.assertIsNone(certificate.fingerprint_sha256)
        self.assertEqual(str(certificate), "Test certificate")

    def test_default_statuses_available(self):
        content_type = ContentType.objects.get_for_model(models.Certificate)
        names = set(Status.objects.filter(content_types=content_type).values_list("name", flat=True))
        self.assertTrue({"Planned", "Active", "Revoked", "Retired"}.issubset(names))

    def test_normalization(self):
        certificate = self._build(
            subject_alternative_names=["WWW.Example.com", "www.example.com", "10.0.0.1"],
            serial_number="0A:1B:2C",
            fingerprint_sha256=":".join(["AB"] * 32),
        )
        certificate.validated_save()
        self.assertEqual(certificate.subject_alternative_names, ["www.example.com", "10.0.0.1"])
        self.assertEqual(certificate.serial_number, "0a1b2c")
        self.assertEqual(certificate.fingerprint_sha256, "ab" * 32)

    def test_several_certificates_without_fingerprint(self):
        self._build(name="One").validated_save()
        self._build(name="Two").validated_save()
        self.assertEqual(models.Certificate.objects.filter(fingerprint_sha256__isnull=True).count(), 4)

    def test_fingerprint_is_unique(self):
        with self.assertRaises(ValidationError):
            self._build(fingerprint_sha256="a" * 64).validated_save()

    def test_invalid_values(self):
        cases = {
            "subject_alternative_names": ["not a valid name"],
            "extended_key_usage": ["anyUsage"],
            "serial_number": "xyz",
            "fingerprint_sha256": "abc",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as context:
                    self._build(**{field: value}).full_clean()
                self.assertIn(field, context.exception.message_dict)

    def test_not_before_after_not_after(self):
        certificate = self._build(not_before=timezone.now() + timedelta(days=60))
        with self.assertRaises(ValidationError) as context:
            certificate.full_clean()
        self.assertIn("not_after", context.exception.message_dict)

    def test_cannot_replace_itself(self):
        certificate = models.Certificate.objects.get(name="Wildcard edge")
        certificate.replaces = certificate
        with self.assertRaises(ValidationError) as context:
            certificate.full_clean()
        self.assertIn("replaces", context.exception.message_dict)

    def test_replaced_by(self):
        old = models.Certificate.objects.get(name="www.example.com 2025")
        self.assertEqual(list(old.replaced_by.values_list("name", flat=True)), ["www.example.com 2026"])

    def test_pem_with_private_key_is_rejected(self):
        pem, _, private_key = certificates.build_certificate()
        with self.assertRaises(ValidationError) as context:
            self._build(pem=pem + certificates.private_key_pem(private_key)).full_clean()
        self.assertIn("pem", context.exception.message_dict)

    def test_pem_fingerprint_mismatch(self):
        pem = certificates.build_certificate()[0]
        with self.assertRaises(ValidationError) as context:
            self._build(pem=pem, fingerprint_sha256="d" * 64).full_clean()
        self.assertIn("fingerprint_sha256", context.exception.message_dict)

    def test_pem_matching_fingerprint(self):
        pem, certificate, _ = certificates.build_certificate()
        self._build(pem=pem, fingerprint_sha256=certificates.fingerprint(certificate)).validated_save()

    def test_computed_properties(self):
        expired = models.Certificate.objects.get(name="www.example.com 2025")
        self.assertTrue(expired.is_expired)
        self.assertLess(expired.days_remaining, 0)
        self.assertFalse(expired.is_wildcard)
        wildcard = models.Certificate.objects.get(name="Wildcard edge")
        self.assertFalse(wildcard.is_expired)
        self.assertIn(wildcard.days_remaining, (19, 20))
        self.assertTrue(wildcard.is_wildcard)

    def test_chain(self):
        """A certificate chain is its issuing CA followed by the issuers up to the Root CA."""
        issuing = models.CertificateAuthority.objects.get(name="Internal Issuing CA")
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        self.assertEqual(self._build(certificate_authority=issuing).chain, [issuing, root])
        self.assertEqual(self._build().chain, [])

    def test_ca_delete_protected(self):
        with self.assertRaises(ProtectedError):
            models.CertificateAuthority.objects.get(name="Internal Issuing CA").delete()
