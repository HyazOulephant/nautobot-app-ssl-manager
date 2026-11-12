"""Tests for the link between a Certificate Authority and its own CA certificate."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from nautobot.apps.testing import TestCase

from nautobot_ssl_manager import filters, forms, models, utils
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures


def create_certificate(name, pem="", **kwargs):
    """Create a Certificate (optionally from a PEM, whose data is then used)."""
    if pem:
        parsed = utils.parse_pem_certificate(pem)
        kwargs.setdefault("common_name", parsed.common_name)
        kwargs.setdefault("fingerprint_sha256", parsed.fingerprint_sha256)
        kwargs.setdefault("not_after", parsed.not_after)
    kwargs.setdefault("common_name", name)
    kwargs.setdefault("not_after", timezone.now() + timedelta(days=3650))
    kwargs.setdefault("status", fixtures.get_certificate_statuses()[1])
    return models.Certificate.objects.create(name=name, pem=pem, **kwargs)


class CACertificateTestCase(TestCase):
    """Base test case. Lab Root CA (Root) -> Internal Issuing CA (Intermediate), from the fixtures."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificates()
        cls.root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        cls.intermediate = models.CertificateAuthority.objects.get(name="Internal Issuing CA")


class UtilsTest(TestCase):
    """CA facts read from the PEM."""

    def test_ca_flag_and_distinguished_names(self):
        parsed = utils.parse_pem_certificate(
            certificates.build_certificate(common_name="Lab Root CA", issuer_common_name="Lab Root CA", is_ca=True)[0]
        )
        self.assertTrue(parsed.is_ca)
        self.assertEqual(parsed.subject_dn, "CN=Lab Root CA")
        self.assertEqual(parsed.issuer_dn, "CN=Lab Root CA")
        self.assertFalse(utils.parse_pem_certificate(certificates.build_certificate()[0]).is_ca)


class CACertificateModelTest(CACertificateTestCase):
    """Validation of the CA certificate."""

    def test_link_and_reverse_link(self):
        certificate = create_certificate("Lab Root CA certificate", certificate_authority=self.root)
        self.root.certificate = certificate
        self.root.validated_save()
        certificate.refresh_from_db()
        self.assertEqual(certificate.ca_certificate_authority, self.root)
        self.assertIsNone(models.Certificate.objects.get(name="Wildcard edge").ca_certificate_authority)
        self.assertIsNone(models.Certificate(name="new").ca_certificate_authority)

    def test_certificate_linked_to_one_ca_only(self):
        certificate = create_certificate("Shared certificate")
        self.root.certificate = certificate
        self.root.validated_save()
        self.intermediate.certificate = certificate
        with self.assertRaises(ValidationError) as context:
            self.intermediate.validated_save()
        self.assertIn("certificate", context.exception.message_dict)

    def test_deleting_the_certificate_unlinks_it(self):
        certificate = create_certificate("Lab Root CA certificate")
        self.root.certificate = certificate
        self.root.validated_save()
        certificate.delete()
        self.root.refresh_from_db()
        self.assertIsNone(self.root.certificate)

    def test_pem_must_be_a_ca_certificate(self):
        pem = certificates.build_certificate(common_name="Lab Root CA", issuer_common_name="Lab Root CA")[0]
        self.root.certificate = create_certificate("Not a CA", pem=pem)
        with self.assertRaisesMessage(ValidationError, "basicConstraints CA:TRUE"):
            self.root.validated_save()

    def test_root_ca_certificate_issued_by_another_ca(self):
        self.root.certificate = create_certificate(
            "Issued by Sectigo",
            certificate_authority=models.CertificateAuthority.objects.get(name="Sectigo RSA Domain Validation"),
        )
        with self.assertRaisesMessage(ValidationError, "but the CA is issued by the CA itself (Root CA)"):
            self.root.validated_save()

    def test_intermediate_ca_certificate_issued_by_another_ca(self):
        self.intermediate.certificate = create_certificate("Self-issued", certificate_authority=self.intermediate)
        with self.assertRaisesMessage(ValidationError, "but the CA is issued by Lab Root CA"):
            self.intermediate.validated_save()

    def test_issuer_dn_must_match_parent_certificate_subject(self):
        root_pem = certificates.build_certificate(
            common_name="Lab Root CA", issuer_common_name="Lab Root CA", is_ca=True
        )[0]
        self.root.certificate = create_certificate("Lab Root CA certificate", pem=root_pem)
        self.root.validated_save()

        wrong_pem = certificates.build_certificate(
            common_name="Internal Issuing CA", issuer_common_name="Other Root CA", is_ca=True
        )[0]
        self.intermediate.certificate = create_certificate("Wrong issuer", pem=wrong_pem)
        with self.assertRaisesMessage(ValidationError, "does not match the subject of the certificate of Lab Root CA"):
            self.intermediate.validated_save()

        good_pem = certificates.build_certificate(
            common_name="Internal Issuing CA", issuer_common_name="Lab Root CA", is_ca=True
        )[0]
        self.intermediate.certificate = create_certificate(
            "Internal Issuing CA certificate", pem=good_pem, certificate_authority=self.root
        )
        self.intermediate.validated_save()

    def test_parent_without_certificate_skips_issuer_dn_check(self):
        pem = certificates.build_certificate(
            common_name="Internal Issuing CA", issuer_common_name="Anything", is_ca=True
        )[0]
        self.intermediate.certificate = create_certificate("Internal Issuing CA certificate", pem=pem)
        self.intermediate.validated_save()

    def test_linked_certificate_edit_is_validated(self):
        certificate = create_certificate("Lab Root CA certificate", certificate_authority=self.root)
        self.root.certificate = certificate
        self.root.validated_save()

        certificate.refresh_from_db()
        certificate.certificate_authority = self.intermediate
        with self.assertRaises(ValidationError) as context:
            certificate.validated_save()
        self.assertIn("certificate_authority", context.exception.message_dict)

        certificate.refresh_from_db()
        pem = certificates.build_certificate(common_name="Lab Root CA", issuer_common_name="Lab Root CA")[0]
        certificate.pem = pem
        certificate.fingerprint_sha256 = None
        with self.assertRaises(ValidationError) as context:
            certificate.validated_save()
        self.assertIn("pem", context.exception.message_dict)


class CACertificateFilterTest(CACertificateTestCase):
    """Filters related to the CA certificate."""

    @classmethod
    def setUpTestData(cls):
        """Link the Root CA to its certificate."""
        super().setUpTestData()
        cls.certificate = fixtures.create_ca_certificate()

    def test_has_certificate(self):
        filterset = filters.CertificateAuthorityFilterSet
        queryset = models.CertificateAuthority.objects.all()
        self.assertQuerysetEqualAndNotEmpty(
            filterset({"has_certificate": True}, queryset).qs, queryset.filter(pk=self.root.pk)
        )
        self.assertQuerysetEqualAndNotEmpty(
            filterset({"has_certificate": False}, queryset).qs, queryset.exclude(pk=self.root.pk)
        )

    def test_certificate(self):
        filterset = filters.CertificateAuthorityFilterSet
        queryset = models.CertificateAuthority.objects.all()
        for value in (self.certificate.pk, self.certificate.name):
            self.assertQuerysetEqualAndNotEmpty(
                filterset({"certificate": [value]}, queryset).qs, queryset.filter(pk=self.root.pk)
            )

    def test_is_ca_certificate(self):
        filterset = filters.CertificateFilterSet
        queryset = models.Certificate.objects.all()
        self.assertQuerysetEqualAndNotEmpty(
            filterset({"is_ca_certificate": True}, queryset).qs, queryset.filter(pk=self.certificate.pk)
        )
        self.assertQuerysetEqualAndNotEmpty(
            filterset({"is_ca_certificate": False}, queryset).qs, queryset.exclude(pk=self.certificate.pk)
        )


class CACertificateFormTest(CACertificateTestCase):
    """CA form: CA certificate field and suggestions."""

    def _data(self, **kwargs):
        return {
            "name": self.root.name,
            "type": CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            "status": self.root.status.pk,
            **kwargs,
        }

    def test_link_from_the_form(self):
        certificate = create_certificate("Lab Root CA certificate", certificate_authority=self.root)
        form = forms.CertificateAuthorityForm(data=self._data(certificate=certificate.pk), instance=self.root)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().certificate, certificate)

    def test_inconsistent_certificate_rejected(self):
        certificate = create_certificate("Issued by the intermediate", certificate_authority=self.intermediate)
        form = forms.CertificateAuthorityForm(data=self._data(certificate=certificate.pk), instance=self.root)
        self.assertFalse(form.is_valid())
        self.assertIn("certificate", form.errors)

    def test_suggestions_in_help_text(self):
        create_certificate("Lab Root CA 2036", common_name="lab root ca")
        form = forms.CertificateAuthorityForm(instance=self.root)
        self.assertIn(
            "Suggestions (same Common Name as the CA): Lab Root CA 2036", form.fields["certificate"].help_text
        )
        self.assertIsNone(form.initial.get("certificate"))
        self.assertNotIn("Suggestions", forms.CertificateAuthorityForm().fields["certificate"].help_text)


class CACertificateViewTest(CACertificateTestCase):
    """Detail views and PEM import hint."""

    user_permissions = [
        "nautobot_ssl_manager.add_certificate",
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
    ]

    def test_detail_views(self):
        certificate = create_certificate("Lab Root CA certificate", certificate_authority=self.root)
        self.root.certificate = certificate
        self.root.validated_save()

        content = self.client.get(self.root.get_absolute_url()).content.decode()
        self.assertIn("CA certificate expires", content)
        self.assertIn(certificate.get_absolute_url(), content)

        content = self.client.get(certificate.get_absolute_url()).content.decode()
        self.assertIn("CA certificate of", content)
        self.assertIn(self.root.get_absolute_url(), content)

    def test_list_view_optional_columns(self):
        url = reverse("plugins:nautobot_ssl_manager:certificateauthority_list")
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        table = response.context["table"]
        self.assertIn("certificate", table.base_columns)
        self.assertIn("certificate_expires", table.base_columns)

    def test_import_ca_certificate_suggests_the_ca(self):
        pem = certificates.build_certificate(common_name="Lab Root CA", issuer_common_name="Lab Root CA", is_ca=True)[0]
        url = reverse("plugins:nautobot_ssl_manager:certificate_import_pem")
        response = self.client.post(url, {"pem": pem}, follow=True)
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn("This is a CA certificate", content)
        self.assertIn("Suggested Certificate Authority (same name as the Common Name): Lab Root CA", content)
        self.assertIsNone(models.CertificateAuthority.objects.get(pk=self.root.pk).certificate)

    def test_import_leaf_certificate_has_no_hint(self):
        url = reverse("plugins:nautobot_ssl_manager:certificate_import_pem")
        response = self.client.post(url, {"pem": certificates.build_certificate()[0]}, follow=True)
        self.assertNotIn("This is a CA certificate", response.content.decode())
