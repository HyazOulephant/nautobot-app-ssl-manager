"""Tests for certificate downloads (certificate only and certificate with chain)."""

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7
from django.urls import reverse
from nautobot.apps.testing import APITestCase, TestCase

from nautobot_ssl_manager import downloads, models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures
from nautobot_ssl_manager.tests.test_ca_certificate import create_certificate


def common_names(loaded_certificates):
    """Common Names of x509 certificates, in order."""
    return [
        loaded.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value for loaded in loaded_certificates
    ]


class ChainTestData:  # pylint: disable=too-few-public-methods
    """Chain: Download Root CA (self-signed) -> Download Issuing CA -> www.example.com."""

    @classmethod
    def create_chain(cls):
        """Create the CAs, their certificates and the leaf certificate."""
        status = fixtures.get_certificate_authority_statuses()[0]
        cls.root = models.CertificateAuthority.objects.create(
            name="Download Root CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=status
        )
        cls.issuing = models.CertificateAuthority.objects.create(
            name="Download Issuing CA",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=status,
            parent=cls.root,
        )
        cls.root.certificate = create_certificate(
            "Download Root CA certificate",
            pem=certificates.build_certificate(
                common_name="Download Root CA", issuer_common_name="Download Root CA", is_ca=True, dns_names=()
            )[0],
            certificate_authority=cls.root,
        )
        cls.root.validated_save()
        cls.issuing.certificate = create_certificate(
            "Download Issuing CA certificate",
            pem=certificates.build_certificate(
                common_name="Download Issuing CA", issuer_common_name="Download Root CA", is_ca=True, dns_names=()
            )[0],
            certificate_authority=cls.root,
        )
        cls.issuing.validated_save()
        cls.leaf = create_certificate(
            "www.example.com download",
            pem=certificates.build_certificate(common_name="*.example.com", issuer_common_name="Download Issuing CA")[
                0
            ],
            certificate_authority=cls.issuing,
        )


class BuildDownloadTest(ChainTestData, TestCase):
    """File content, order, formats and errors."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.create_chain()

    def test_safe_filename_base(self):
        self.assertEqual(downloads.safe_filename_base(self.leaf), "wildcard.example.com")
        self.assertEqual(downloads.safe_filename_base(models.Certificate(common_name="../a b/c")), "a_b_c")
        self.assertEqual(downloads.safe_filename_base(models.Certificate(common_name="/")), "certificate")

    def test_certificate_pem(self):
        download = downloads.build_download(self.leaf)
        self.assertEqual(download.filename, "wildcard.example.com.pem")
        self.assertEqual(download.content_type, "application/x-pem-file")
        self.assertEqual(download.content.decode(), self.leaf.pem)

    def test_certificate_der(self):
        download = downloads.build_download(self.leaf, file_format="DER")
        self.assertEqual(download.filename, "wildcard.example.com.der")
        self.assertEqual(download.content_type, "application/pkix-cert")
        self.assertEqual(common_names([x509.load_der_x509_certificate(download.content)]), ["*.example.com"])

    def test_chain_pem_without_root(self):
        download = downloads.build_download(self.leaf, chain=True)
        self.assertEqual(download.filename, "wildcard.example.com-chain.pem")
        self.assertEqual(
            common_names(x509.load_pem_x509_certificates(download.content)), ["*.example.com", "Download Issuing CA"]
        )

    def test_chain_pem_with_root(self):
        download = downloads.build_download(self.leaf, chain=True, include_root=True)
        self.assertEqual(download.filename, "wildcard.example.com-chain-with-root.pem")
        self.assertEqual(
            common_names(x509.load_pem_x509_certificates(download.content)),
            ["*.example.com", "Download Issuing CA", "Download Root CA"],
        )

    def test_chain_p7b_with_root(self):
        download = downloads.build_download(self.leaf, file_format="p7b", chain=True, include_root=True)
        self.assertEqual(download.filename, "wildcard.example.com-chain-with-root.p7b")
        self.assertEqual(download.content_type, "application/x-pkcs7-certificates")
        # PKCS#7 stores the certificates in a DER SET: their order is not significant.
        self.assertCountEqual(
            common_names(pkcs7.load_der_pkcs7_certificates(download.content)),
            ["*.example.com", "Download Issuing CA", "Download Root CA"],
        )

    def test_root_ca_certificate_is_not_duplicated(self):
        download = downloads.build_download(self.root.certificate, chain=True, include_root=True)
        self.assertEqual(common_names(x509.load_pem_x509_certificates(download.content)), ["Download Root CA"])

    def test_invalid_requests(self):
        for kwargs, message in (
            ({"file_format": "pfx"}, "Unsupported format"),
            ({"file_format": "der", "chain": True}, "single certificate"),
        ):
            with self.assertRaisesMessage(downloads.CertificateDownloadError, message):
                downloads.build_download(self.leaf, **kwargs)

    def test_no_pem(self):
        certificate = create_certificate("No PEM", certificate_authority=self.issuing)
        with self.assertRaisesMessage(downloads.CertificateDownloadError, "No PEM is stored"):
            downloads.build_download(certificate)
        self.assertEqual(downloads.chain_unavailable_reason(certificate), "No PEM is stored for this certificate.")

    def test_no_certificate_authority(self):
        self.leaf.certificate_authority = None
        with self.assertRaisesMessage(downloads.CertificateDownloadError, "No Certificate Authority is set"):
            downloads.build_download(self.leaf, chain=True)

    def test_incomplete_chain_lists_the_missing_cas(self):
        self.root.certificate = None
        self.root.save()
        with self.assertRaisesMessage(downloads.CertificateDownloadError, "no CA certificate linked: Download Root CA"):
            downloads.build_download(self.leaf, chain=True)
        self.assertIn("Download Root CA", downloads.chain_unavailable_reason(self.leaf))
        # The certificate alone can still be downloaded.
        downloads.build_download(self.leaf)

    def test_ca_certificate_without_pem(self):
        models.Certificate.objects.filter(pk=self.issuing.certificate_id).update(pem="")
        with self.assertRaisesMessage(
            downloads.CertificateDownloadError, "CA certificate without PEM: Download Issuing CA"
        ):
            downloads.build_download(self.leaf, chain=True)

    def test_inconsistent_chain(self):
        other = certificates.build_certificate(common_name="www.other.com", issuer_common_name="Other CA")[0]
        models.Certificate.objects.filter(pk=self.leaf.pk).update(pem=other)
        self.leaf.refresh_from_db()
        with self.assertRaisesMessage(downloads.CertificateDownloadError, "The chain is inconsistent"):
            downloads.build_download(self.leaf, chain=True)


class DownloadViewTest(ChainTestData, TestCase):
    """UI download view and Download menu."""

    user_permissions = [
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
    ]

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.create_chain()

    def _url(self, certificate, **params):
        url = reverse("plugins:nautobot_ssl_manager:certificate_download", kwargs={"pk": certificate.pk})
        return f"{url}?{'&'.join(f'{key}={value}' for key, value in params.items())}"

    def test_download_attachment(self):
        response = self.client.get(self._url(self.leaf, file_format="pem", chain="true", include_root="true"))
        self.assertHttpStatus(response, 200)
        self.assertEqual(response["Content-Type"], "application/x-pem-file")
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="wildcard.example.com-chain-with-root.pem"'
        )
        self.assertEqual(len(x509.load_pem_x509_certificates(response.content)), 3)

    def test_error_redirects_with_message(self):
        self.root.certificate = None
        self.root.save()
        response = self.client.get(self._url(self.leaf, chain="true"), follow=True)
        self.assertHttpStatus(response, 200)
        self.assertIn("Download failed: The chain is incomplete", response.content.decode())

    def test_chain_requires_ca_permission(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificateauthority")
        response = self.client.get(self._url(self.leaf, chain="true"), follow=True)
        self.assertIn("Viewing Certificate Authorities is required", response.content.decode())
        self.assertHttpStatus(self.client.get(self._url(self.leaf)), 200)

    def test_requires_view_certificate(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificate")
        self.assertHttpStatus(self.client.get(self._url(self.leaf)), 403)

    def test_download_menu(self):
        content = self.client.get(self.leaf.get_absolute_url()).content.decode()
        self.assertIn("Certificate + chain + root (PKCS#7)", content)
        self.assertIn(
            self._url(self.leaf, file_format="p7b", chain="true", include_root="true"), content.replace("&amp;", "&")
        )

    def test_download_menu_disabled_entries(self):
        certificate = create_certificate("No PEM", certificate_authority=self.issuing)
        content = self.client.get(certificate.get_absolute_url()).content.decode()
        self.assertIn('title="No PEM is stored for this certificate."', content)

    def test_download_menu_without_ca_permission(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificateauthority")
        content = self.client.get(self.leaf.get_absolute_url()).content.decode()
        self.assertIn("Certificate (DER)", content)
        self.assertNotIn("Certificate + chain", content)


class DownloadAPITest(ChainTestData, APITestCase):  # pylint: disable=too-many-ancestors
    """REST API download endpoint."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.create_chain()

    def setUp(self):
        super().setUp()
        self.add_permissions("nautobot_ssl_manager.view_certificate", "nautobot_ssl_manager.view_certificateauthority")

    def _url(self, certificate):
        return reverse("plugins-api:nautobot_ssl_manager-api:certificate-download", kwargs={"pk": certificate.pk})

    def test_download_certificate(self):
        response = self.client.get(self._url(self.leaf), **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(response.content.decode(), self.leaf.pem)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="wildcard.example.com.pem"')

    def test_download_chain_p7b(self):
        response = self.client.get(
            self._url(self.leaf), {"file_format": "p7b", "chain": "true", "include_root": "true"}, **self.header
        )
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(pkcs7.load_der_pkcs7_certificates(response.content)), 3)

    def test_incomplete_chain(self):
        self.root.certificate = None
        self.root.save()
        response = self.client.get(self._url(self.leaf), {"chain": "true"}, **self.header)
        self.assertHttpStatus(response, 400)
        self.assertIn("Download Root CA", response.json()["detail"])

    def test_chain_requires_ca_permission(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificateauthority")
        response = self.client.get(self._url(self.leaf), {"chain": "true"}, **self.header)
        self.assertHttpStatus(response, 403)

    def test_requires_view_certificate(self):
        self.remove_permissions("nautobot_ssl_manager.view_certificate")
        self.assertHttpStatus(self.client.get(self._url(self.leaf), **self.header), 403)
