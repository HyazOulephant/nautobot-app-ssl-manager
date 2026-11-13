"""Tests for the identification of the issuing CA by signature verification."""

from unittest import mock

from cryptography import x509
from django.urls import reverse
from nautobot.apps.testing import TestCase

from nautobot_ssl_manager import forms, issuers, models, utils
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures
from nautobot_ssl_manager.tests.test_ca_certificate import create_certificate


class IssuerTestCase(TestCase):
    """Chain with key identifiers: Issuer Root CA -> Issuer Issuing CA -> www.issuer.example.com.

    In Nautobot, the Issuing CA is named "Renamed Issuing CA" (not its Common Name), and a homonymous CA named like the
    issuer Common Name exists without CA certificate.
    """

    user_permissions = [
        "nautobot_ssl_manager.add_certificate",
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
        "nautobot_ssl_manager.change_certificateauthority",
    ]

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.root_pem, cls.intermediate_pem, cls.leaf_pem = certificates.build_chain(
            root="Issuer Root CA", intermediate="Issuer Issuing CA", leaf="www.issuer.example.com", key_identifiers=True
        )
        status = fixtures.get_certificate_authority_statuses()[0]
        cls.root = models.CertificateAuthority.objects.create(
            name="Issuer Root CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
        )
        cls.root.certificate = create_certificate("Issuer Root CA", pem=cls.root_pem, certificate_authority=cls.root)
        cls.root.validated_save()
        cls.intermediate = models.CertificateAuthority.objects.create(
            name="Renamed Issuing CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status, parent=cls.root
        )
        cls.intermediate.certificate = create_certificate(
            "Issuer Issuing CA", pem=cls.intermediate_pem, certificate_authority=cls.root
        )
        cls.intermediate.validated_save()
        cls.homonym = models.CertificateAuthority.objects.create(
            name="Issuer Issuing CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
        )

    def leaf(self):
        """Parsed leaf certificate."""
        return utils.parse_pem_certificate(self.leaf_pem)


class IssuerIdentificationTest(IssuerTestCase):
    """`issuers.find_issuing_authorities` and `issuers.identify_issuer`."""

    def test_key_identifiers(self):
        leaf = self.leaf().certificate
        intermediate = x509.load_pem_x509_certificate(self.intermediate_pem.encode())
        self.assertEqual(utils.authority_key_identifier(leaf), utils.subject_key_identifier(intermediate))
        without = x509.load_pem_x509_certificate(certificates.build_certificate()[0].encode())
        self.assertIsNone(utils.authority_key_identifier(without))
        self.assertIsNone(utils.subject_key_identifier(without))

    def test_proven_by_signature_not_by_name(self):
        identification = issuers.identify_issuer(self.leaf())
        self.assertEqual(identification.method, issuers.METHOD_SIGNATURE)
        self.assertEqual(identification.proven_authority, self.intermediate)

    def test_key_identifiers_preselect_the_candidates(self):
        with mock.patch.object(issuers.utils, "is_issued_by", wraps=utils.is_issued_by) as verify:
            issuers.find_issuing_authorities(self.leaf().certificate)
        # The Root CA certificate has another Subject Key Identifier: its signature is not even checked.
        self.assertEqual(verify.call_count, 1)

    def test_without_key_identifiers(self):
        _, intermediate_pem, leaf_pem = certificates.build_chain(
            root="Plain Root CA", intermediate="Plain Issuing CA", leaf="www.plain.example.com"
        )
        authority = models.CertificateAuthority.objects.create(
            name="Plain CA",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=fixtures.get_certificate_authority_statuses()[0],
        )
        authority.certificate = create_certificate("Plain Issuing CA", pem=intermediate_pem)
        authority.validated_save()
        identification = issuers.identify_issuer(utils.parse_pem_certificate(leaf_pem))
        self.assertEqual(identification.proven_authority, authority)

    def test_ambiguous(self):
        # Same subject and key as the Issuing CA certificate, issued again: both CA certificates verify the leaf.
        _, _, root_key = certificates.build_certificate(
            common_name="Twin Root CA", issuer_common_name="Twin Root CA", is_ca=True, dns_names=(), eku=()
        )
        first_pem, _, intermediate_key = certificates.build_certificate(
            common_name="Twin CA",
            issuer_common_name="Twin Root CA",
            is_ca=True,
            dns_names=(),
            eku=(),
            issuer_key=root_key,
        )
        second_pem = certificates.build_certificate(
            common_name="Twin CA",
            issuer_common_name="Twin Root CA",
            is_ca=True,
            dns_names=(),
            eku=(),
            issuer_key=root_key,
            private_key=intermediate_key,
            days=365,
        )[0]
        leaf_pem = certificates.build_certificate(
            common_name="www.twin.example.com", issuer_common_name="Twin CA", issuer_key=intermediate_key
        )[0]
        status = fixtures.get_certificate_authority_statuses()[0]
        for name, pem in (("Twin CA one", first_pem), ("Twin CA two", second_pem)):
            authority = models.CertificateAuthority.objects.create(
                name=name, type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
            )
            authority.certificate = create_certificate(name, pem=pem)
            authority.validated_save()
        identification = issuers.identify_issuer(utils.parse_pem_certificate(leaf_pem))
        self.assertEqual(identification.method, issuers.METHOD_AMBIGUOUS)
        self.assertEqual({str(ca) for ca in identification.authorities}, {"Twin CA one", "Twin CA two"})
        self.assertIsNone(identification.proven_authority)

    def test_name_match_is_only_a_suggestion(self):
        pem = certificates.build_certificate(
            common_name="www.other.example.com", issuer_common_name="Issuer Issuing CA"
        )[0]
        identification = issuers.identify_issuer(utils.parse_pem_certificate(pem))
        self.assertEqual(identification.method, issuers.METHOD_NAME)
        self.assertEqual(identification.authorities, [self.homonym])
        self.assertIsNone(identification.proven_authority)

    def test_nothing_found(self):
        pem = certificates.build_certificate(issuer_common_name="Unknown CA")[0]
        identification = issuers.identify_issuer(utils.parse_pem_certificate(pem))
        self.assertIsNone(identification.method)
        self.assertEqual(identification.authorities, [])


class IssuerImportViewTest(IssuerTestCase):
    """PEM import of a single certificate."""

    def _import(self, pem):
        url = reverse("plugins:nautobot_ssl_manager:certificate_import_pem")
        return self.client.post(url, {"pem": pem}, follow=True)

    def test_proven_issuer_is_preselected(self):
        response = self._import(self.leaf_pem)
        form = response.context["form"]
        self.assertEqual(form.initial["certificate_authority"], str(self.intermediate.pk))
        content = response.content.decode()
        self.assertRegex(content, rf'<option value="{self.intermediate.pk}"\s+selected\s*>')
        self.assertIn(
            "Pre-selected: the signature of the certificate is verified with the CA certificate of Renamed Issuing CA",
            content,
        )
        self.assertNotIn("is not in Nautobot", content)

    def test_name_match_is_not_preselected(self):
        pem = certificates.build_certificate(
            common_name="www.other.example.com", issuer_common_name="Issuer Issuing CA"
        )[0]
        response = self._import(pem)
        self.assertIsNone(response.context["form"].initial.get("certificate_authority"))
        self.assertIn(
            "Suggestion, not verified (same name as the issuer Common Name): Issuer Issuing CA",
            response.content.decode(),
        )

    def test_issuer_not_visible_is_not_named(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificateauthority")
        self.add_permissions("nautobot_ssl_manager.view_certificate")
        response = self._import(self.leaf_pem)
        self.assertNotIn("Renamed Issuing CA", response.content.decode())

    def test_ca_certificate_issuer_hint(self):
        # A new chain, so that the intermediate CA certificate is not already in Nautobot.
        root_pem, intermediate_pem, _ = certificates.build_chain(
            root="Hint Root CA", intermediate="Hint Issuing CA", leaf="www.hint.example.com"
        )
        authority = models.CertificateAuthority.objects.create(
            name="Hint Root CA",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=fixtures.get_certificate_authority_statuses()[0],
        )
        authority.certificate = create_certificate("Hint Root CA", pem=root_pem, certificate_authority=authority)
        authority.validated_save()
        content = self._import(intermediate_pem).content.decode()
        self.assertIn("Its issuer, proven by signature, is Hint Root CA", content)

    def test_self_signed_ca_certificate_hint(self):
        pem = certificates.build_certificate(
            common_name="New Root CA", issuer_common_name="New Root CA", is_ca=True, dns_names=()
        )[0]
        content = self._import(pem).content.decode()
        self.assertIn("It is self-signed: its Certificate Authority is a Root CA", content)


class ParentHintTest(IssuerTestCase):
    """CA form: Issued by suggested from the CA certificate."""

    def test_parent_hint(self):
        root_pem, intermediate_pem, _ = certificates.build_chain(
            root="Parent Root CA", intermediate="Parent Issuing CA", leaf="www.parent.example.com"
        )
        status = fixtures.get_certificate_authority_statuses()[0]
        root = models.CertificateAuthority.objects.create(
            name="Parent Root CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
        )
        root.certificate = create_certificate("Parent Root CA", pem=root_pem, certificate_authority=root)
        root.validated_save()
        orphan = models.CertificateAuthority.objects.create(
            name="Parent Issuing CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
        )
        orphan.certificate = create_certificate("Parent Issuing CA", pem=intermediate_pem)
        orphan.validated_save()

        help_text = forms.CertificateAuthorityForm(instance=orphan).fields["parent"].help_text
        self.assertIn("Suggestion, proven by the signature of its CA certificate: Parent Root CA.", help_text)
        self.assertIsNone(forms.CertificateAuthorityForm(instance=orphan).initial.get("parent"))
        root_help_text = forms.CertificateAuthorityForm(instance=root).fields["parent"].help_text
        self.assertIn("Its CA certificate is self-signed", root_help_text)
