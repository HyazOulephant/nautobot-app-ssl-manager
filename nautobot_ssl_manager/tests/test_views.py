"""UI view tests for nautobot_ssl_manager."""

from datetime import datetime, timezone

from django.urls import reverse
from nautobot.apps.testing import TestCase, ViewTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures


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


class CertificateViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the Certificate views."""

    model = models.Certificate

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificates()
        _, active, revoked, _ = fixtures.get_certificate_statuses()
        authority = models.CertificateAuthority.objects.get(name="Lab Root CA")
        cls.form_data = {
            "name": "View certificate",
            "common_name": "view.example.com",
            "subject_alternative_names": ["view.example.com", "10.2.2.2"],
            "status": active.pk,
            "not_after": datetime(2030, 6, 1, tzinfo=timezone.utc),
            "certificate_authority": authority.pk,
            "extended_key_usage": ["serverAuth", "clientAuth"],
            "auto_renew": True,
            "order_number": "ORD-VIEW",
        }
        cls.update_data = {
            "name": "View certificate updated",
            "common_name": "view.example.com",
            "not_after": datetime(2031, 1, 1, tzinfo=timezone.utc),
            "status": revoked.pk,
        }
        cls.bulk_edit_data = {"description": "Bulk edit views", "status": revoked.pk}


class CertificateImportPEMViewTest(TestCase):
    """Test the PEM import workflow."""

    user_permissions = [
        "nautobot_ssl_manager.add_certificate",
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
    ]

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificates()

    def setUp(self):
        super().setUp()
        self.url = reverse("plugins:nautobot_ssl_manager:certificate_import_pem")

    def test_get(self):
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 200)
        self.assertIn("PEM certificate", response.content.decode())

    def test_permission_required(self):
        self.remove_permissions("nautobot_ssl_manager.add_certificate")
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 403)

    def test_import_prefills_creation_form(self):
        authority = models.CertificateAuthority.objects.get(name="Lab Root CA")
        pem, certificate, _ = certificates.build_certificate(
            common_name="www.example.com",
            dns_names=("www.example.com", "example.com"),
            issuer_common_name=authority.name,
            policies=(certificates.OV_POLICY,),
        )
        response = self.client.post(self.url, {"pem": pem})
        self.assertHttpStatus(response, 302)
        self.assertIn("pem_import=", response["Location"])

        response = self.client.get(response["Location"])
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn(certificates.fingerprint(certificate), content)
        self.assertIn("www.example.com\nexample.com", content)
        # Suggestions are displayed but never selected automatically.
        self.assertIn("Suggestions (same CN or shared SANs)", content)
        self.assertIn("www.example.com 2026", content)
        # The CA is pre-selected in the rendered form (the option tag spans several lines).
        self.assertRegex(content, rf'<option value="{authority.pk}"\s+selected\s*>')
        form = response.context["form"]
        self.assertEqual(form.initial["certificate_authority"], str(authority.pk))
        self.assertIsNone(form.initial.get("replaces"))
        self.assertEqual(form.initial["validation_level"], "ov")

    def test_import_private_key_rejected(self):
        pem, _, private_key = certificates.build_certificate()
        response = self.client.post(self.url, {"pem": pem + certificates.private_key_pem(private_key)})
        self.assertHttpStatus(response, 200)
        self.assertIn("private key", response.content.decode())
        self.assertNotIn("nautobot_ssl_manager_pem_import", self.client.session)

    def test_issuer_without_exact_match_is_not_proposed(self):
        pem = certificates.build_certificate(issuer_common_name="Unknown CA")[0]
        response = self.client.get(self.client.post(self.url, {"pem": pem})["Location"])
        self.assertIsNone(response.context["form"].initial.get("certificate_authority"))

    def test_expired_token(self):
        response = self.client.get(
            reverse("plugins:nautobot_ssl_manager:certificate_add") + "?pem_import=unknown", follow=True
        )
        self.assertHttpStatus(response, 200)
        self.assertIn("The PEM import has expired", response.content.decode())


class CertificationChainViewTest(TestCase):
    """Test the certification chain panel on Certificate and Certificate Authority detail views."""

    user_permissions = [
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
    ]

    @classmethod
    def setUpTestData(cls):
        """Create test data (chain: Lab Root CA -> Internal Issuing CA -> vpn-client-01)."""
        fixtures.create_certificates()

    def _panel(self, url):
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn('id="certification-chain"', content)
        return content

    def test_certificate_chain(self):
        certificate = models.Certificate.objects.get(name="vpn-client-01")
        content = self._panel(certificate.get_absolute_url())
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        issuing = models.CertificateAuthority.objects.get(name="Internal Issuing CA")
        self.assertIn(root.get_absolute_url(), content)
        self.assertIn(issuing.get_absolute_url(), content)
        self.assertIn("Root CA", content)
        self.assertIn("Intermediate CA", content)
        # Root CA is displayed before the Intermediate CA
        self.assertLess(content.index("Root CA</span>"), content.index("Intermediate CA</span>"))

    def test_certificate_without_ca(self):
        certificate = models.Certificate.objects.filter(certificate_authority__isnull=True).first()
        if certificate is None:
            self.skipTest("No certificate without CA in fixtures")
        self.assertIn("No Certificate Authority set.", self._panel(certificate.get_absolute_url()))

    def test_certificate_authority_chain_and_issued_cas(self):
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        content = self._panel(root.get_absolute_url())
        self.assertIn("issued certificate authorities", content.lower())
        self.assertIn("issued certificates", content.lower())
        self.assertIn("Internal Issuing CA", content)
