"""Test forms for nautobot_ssl_manager."""

from django.test import TestCase

from nautobot_ssl_manager import forms
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import fixtures


class CertificateProviderFormTest(TestCase):
    """Test CertificateProvider forms."""

    def test_specifying_all_fields_success(self):
        tenant = fixtures.create_tenants()[0]
        form = forms.CertificateProviderForm(
            data={
                "name": "Sectigo",
                "description": "Commercial CA vendor",
                "portal_url": "https://sectigo.example.com",
                "tenant": tenant.pk,
                "comments": "Some comments",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

    def test_specifying_only_required_success(self):
        form = forms.CertificateProviderForm(data={"name": "Sectigo"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

    def test_name_is_required(self):
        form = forms.CertificateProviderForm(data={"description": "No name"})
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

    def test_invalid_url(self):
        form = forms.CertificateProviderForm(data={"name": "Sectigo", "portal_url": "not-a-url"})
        self.assertFalse(form.is_valid())
        self.assertIn("portal_url", form.errors)


class CertificateAuthorityFormTest(TestCase):
    """Test CertificateAuthority forms."""

    def setUp(self):
        self.active = fixtures.get_certificate_authority_statuses()[0]

    def test_specifying_only_required_success(self):
        form = forms.CertificateAuthorityForm(
            data={
                "name": "Lab Root CA",
                "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
                "status": self.active.pk,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

    def test_required_fields(self):
        form = forms.CertificateAuthorityForm(data={"description": "Missing everything"})
        self.assertFalse(form.is_valid())
        for field in ("name", "type", "status"):
            self.assertIn("This field is required.", form.errors[field])

    def test_invalid_type(self):
        form = forms.CertificateAuthorityForm(data={"name": "Bad CA", "type": "internal", "status": self.active.pk})
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)
