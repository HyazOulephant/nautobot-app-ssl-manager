"""API tests for nautobot_ssl_manager."""

from datetime import datetime, timedelta, timezone

from nautobot.apps.testing import APIViewTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures


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
        lab_root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        ca_certificate = models.Certificate.objects.create(
            name="API CA Three certificate",
            common_name="API CA Three",
            certificate_authority=lab_root,
            not_after=datetime.now(timezone.utc) + timedelta(days=3650),
            status=fixtures.get_certificate_statuses()[1],
        )
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
                "parent": lab_root.pk,
                "certificate": ca_certificate.pk,
            },
        ]
        cls.update_data = {"name": "API CA Updated", "status": deprecated.pk}
        cls.bulk_update_data = {"description": "Bulk updated"}


class CertificateAPIViewTest(APIViewTestCases.APIViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the API viewsets for Certificate."""

    model = models.Certificate
    choices_fields = ("dcv_method", "key_algorithm", "validation_level")
    # "sha256" is part of the public `fingerprint_sha256` field name, not a password hash.
    VERBOTEN_STRINGS = tuple(
        verboten for verboten in APIViewTestCases.APIViewTestCase.VERBOTEN_STRINGS if verboten != "sha256"
    )

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_certificates()
        _, active, _, retired = fixtures.get_certificate_statuses()
        authority = models.CertificateAuthority.objects.get(name="Lab Root CA")
        pem, certificate, _ = certificates.build_certificate(common_name="api-three.example.com")
        cls.create_data = [
            {
                "name": "API certificate one",
                "common_name": "one.example.com",
                "subject_alternative_names": ["one.example.com", "10.1.1.1"],
                "not_after": datetime(2030, 1, 1, tzinfo=timezone.utc),
                "status": active.pk,
                "certificate_authority": authority.pk,
                "extended_key_usage": ["serverAuth"],
                "auto_renew": True,
            },
            {
                "name": "API certificate two",
                "common_name": "two.example.com",
                "not_after": datetime(2031, 1, 1, tzinfo=timezone.utc),
                "status": retired.pk,
                "key_algorithm": "rsa",
                "key_size": 2048,
            },
            {
                "name": "API certificate three",
                "common_name": "api-three.example.com",
                "not_after": datetime(2032, 1, 1, tzinfo=timezone.utc),
                "status": active.pk,
                "pem": pem,
                "fingerprint_sha256": certificates.fingerprint(certificate),
            },
        ]
        cls.update_data = {"name": "API certificate updated", "auto_renew": False}
        cls.bulk_update_data = {"description": "Bulk updated"}

    def test_invalid_san_rejected(self):
        """Invalid SAN entries are rejected by the API."""
        self.add_permissions("nautobot_ssl_manager.add_certificate", "extras.view_status")
        data = dict(self.create_data[1], name="Invalid SAN", subject_alternative_names=["not valid"])
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertIn("subject_alternative_names", response.json())

    def test_san_normalized(self):
        """SAN entries are normalized when created through the API."""
        self.add_permissions("nautobot_ssl_manager.add_certificate", "extras.view_status")
        data = dict(self.create_data[1], name="Normalized SAN", subject_alternative_names=["WWW.EXAMPLE.COM"])
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, 201)
        self.assertEqual(response.json()["subject_alternative_names"], ["www.example.com"])


class DomainValidationRecordAPIViewTest(APIViewTestCases.APIViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the API viewsets for DomainValidationRecord."""

    model = models.DomainValidationRecord
    choices_fields = ("record_type",)
    # Many-to-many fields are write-only by default in Nautobot REST API responses (see `exclude_m2m`).
    validation_excluded_fields = ["certificates"]
    # "sha256" is part of the `fingerprint_sha256` field name of the nested certificates, not a password hash.
    VERBOTEN_STRINGS = tuple(
        verboten for verboten in APIViewTestCases.APIViewTestCase.VERBOTEN_STRINGS if verboten != "sha256"
    )

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        super().setUpTestData()
        fixtures.create_domain_validation_records()
        certificate = models.Certificate.objects.get(name="www.example.com 2026")
        tenant = fixtures.create_tenants()[0]
        cls.create_data = [
            {
                "record_type": "CNAME",
                "name": "_acme-challenge.shop",
                "zone_name": "example.com",
                "alias": "shop.acme-dns.example.net",
                "certificates": [certificate.pk],
            },
            {"record_type": "TXT", "name": "_validation", "zone_name": "example.org", "text": "token", "ttl": 300},
            {"record_type": "TXT", "name": "", "zone_name": "example.net", "tenant": tenant.pk, "comment": "Apex"},
        ]
        cls.update_data = {"description": "Updated", "ttl": 900}
        cls.bulk_update_data = {"description": "Bulk updated"}

    def test_computed_fields(self):
        """FQDN and comparison with Nautobot DNS Models are read-only fields."""
        self.add_permissions("nautobot_ssl_manager.view_domainvalidationrecord")
        record = models.DomainValidationRecord.objects.get(name="_acme-challenge")
        response = self.client.get(self._get_detail_url(record), **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(response.data["fqdn"], "_acme-challenge.example.com")
        self.assertIn("dns_models_match", response.data)
        self.assertNotIn("_value_hash", response.data)
