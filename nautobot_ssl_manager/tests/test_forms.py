"""Test forms for nautobot_ssl_manager."""

from django.test import TestCase

from nautobot_ssl_manager import forms, models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures


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


class CertificateFormTest(TestCase):
    """Test Certificate forms."""

    def setUp(self):
        self.active = fixtures.get_certificate_statuses()[1]

    def _data(self, **kwargs):
        data = {
            "name": "Form certificate",
            "common_name": "form.example.com",
            "not_after": "2030-01-01 00:00:00",
            "status": self.active.pk,
        }
        data.update(kwargs)
        return data

    def test_only_required(self):
        form = forms.CertificateForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
        certificate = form.save()
        self.assertEqual(certificate.subject_alternative_names, [])
        self.assertIsNone(certificate.auto_renew)

    def test_required_fields(self):
        form = forms.CertificateForm(data={})
        self.assertFalse(form.is_valid())
        for field in ("name", "common_name", "not_after", "status"):
            self.assertIn(field, form.errors)

    def test_san_textarea_and_eku(self):
        form = forms.CertificateForm(
            data=self._data(
                subject_alternative_names="WWW.example.com\n\n*.example.com, 10.0.0.1\nemail:admin@example.com",
                extended_key_usage=["serverAuth", "clientAuth"],
                auto_renew="True",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        certificate = form.save()
        self.assertEqual(
            certificate.subject_alternative_names,
            ["www.example.com", "*.example.com", "10.0.0.1", "email:admin@example.com"],
        )
        self.assertEqual(certificate.extended_key_usage, ["serverAuth", "clientAuth"])
        self.assertTrue(certificate.auto_renew)

    def test_invalid_san(self):
        form = forms.CertificateForm(data=self._data(subject_alternative_names="www.example.com\nnot valid"))
        self.assertFalse(form.is_valid())
        self.assertIn("subject_alternative_names", form.errors)

    def test_edit_renders_sans_one_per_line(self):
        form = forms.CertificateForm(data=self._data(subject_alternative_names="a.example.com\nb.example.com"))
        certificate = form.save() if form.is_valid() else None
        self.assertIsNotNone(certificate, form.errors)
        edit_form = forms.CertificateForm(instance=certificate)
        self.assertIn("a.example.com\nb.example.com", str(edit_form["subject_alternative_names"]))

    def test_replaces_suggestions_in_help_text(self):
        form = forms.CertificateForm(replaces_suggestions=["Old certificate"])
        self.assertIn("Old certificate", form.fields["replaces"].help_text)


class CertificateImportPEMFormTest(TestCase):
    """Test the PEM import form."""

    def test_valid_pem(self):
        pem, certificate, _ = certificates.build_certificate()
        form = forms.CertificateImportPEMForm(data={"pem": pem})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.parsed.fingerprint_sha256, certificates.fingerprint(certificate))

    def test_private_key_rejected(self):
        pem, _, private_key = certificates.build_certificate()
        form = forms.CertificateImportPEMForm(data={"pem": pem + certificates.private_key_pem(private_key)})
        self.assertFalse(form.is_valid())
        self.assertIn("private key", str(form.errors["pem"]))

    def test_duplicate_rejected(self):
        pem, certificate, _ = certificates.build_certificate()
        models.Certificate.objects.create(
            name="Existing",
            common_name="www.example.com",
            fingerprint_sha256=certificates.fingerprint(certificate),
            not_after=certificate.not_valid_after_utc,
            status=fixtures.get_certificate_statuses()[1],
        )
        form = forms.CertificateImportPEMForm(data={"pem": pem})
        self.assertFalse(form.is_valid())
        self.assertIn("already exists", str(form.errors["pem"]))
