"""Tests of the Domain Validation Records and of the optional integration with Nautobot DNS Models."""

from unittest import mock, skipUnless

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from django.urls import reverse
from nautobot.apps.testing import TestCase
from nautobot.users.models import ObjectPermission

from nautobot_ssl_manager import dns_models, filters, forms, models, tables, utils
from nautobot_ssl_manager.choices import DNSModelsMatchChoices, DNSRecordTypeChoices
from nautobot_ssl_manager.tests import fixtures

DNS_MODELS_INSTALLED = apps.is_installed(dns_models.APP_LABEL)


def build_record(**kwargs):
    """Unsaved TXT record with default values."""
    values = {"record_type": DNSRecordTypeChoices.TXT, "name": "_acme-challenge", "zone_name": "example.org"}
    values.update(kwargs)
    return models.DomainValidationRecord(**values)


class NormalizeDNSRecordNameTest(TestCase):
    """Test `utils.normalize_dns_record_name`."""

    def test_normalize(self):
        """Lowercase, without spaces nor trailing dot; underscores are allowed."""
        self.assertEqual(
            utils.normalize_dns_record_name(" _ACME-Challenge.Example.COM. "), "_acme-challenge.example.com"
        )
        self.assertEqual(utils.normalize_dns_record_name(""), "")
        self.assertEqual(utils.normalize_dns_record_name(None), "")

    def test_invalid(self):
        """Empty labels, labels too long and spaces are rejected."""
        for value in ("a..b", "a" * 64 + ".com", "a b.com", ".".join(["a" * 60] * 5)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                utils.normalize_dns_record_name(value)


class DomainValidationRecordModelTest(TestCase):
    """Test the DomainValidationRecord model."""

    def test_fqdn_and_str(self):
        """FQDN from the relative name and the zone, zone apex for an empty name."""
        record = build_record()
        self.assertEqual(record.fqdn, "_acme-challenge.example.org")
        self.assertEqual(str(record), "_acme-challenge.example.org TXT")
        self.assertEqual(build_record(name="").fqdn, "example.org")

    def test_normalization(self):
        """Letter case kept, trailing dot removed; a name qualified with the zone and a dot is made relative."""
        record = build_record(
            record_type=DNSRecordTypeChoices.CNAME,
            name=" _ACME-Challenge.Example.org. ",
            zone_name="Example.ORG.",
            alias="Target.Example.NET.",
        )
        record.validated_save()
        self.assertEqual(record.name, "_ACME-Challenge")
        self.assertEqual(record.zone_name, "Example.ORG")
        self.assertEqual(record.alias, "Target.Example.NET")
        apex = build_record(name="example.org.")
        apex.validated_save()
        self.assertEqual(apex.name, "")

    def test_value(self):
        """Value: alias of a CNAME, text of a TXT."""
        self.assertEqual(build_record(text="token").value, "token")
        self.assertEqual(
            build_record(record_type=DNSRecordTypeChoices.CNAME, alias="a.example.net").value, "a.example.net"
        )

    def test_cname_requires_alias_without_text(self):
        """A CNAME needs an alias and has no text."""
        with self.assertRaises(ValidationError) as context:
            build_record(record_type=DNSRecordTypeChoices.CNAME, text="token").full_clean()
        self.assertIn("alias", context.exception.message_dict)
        self.assertIn("text", context.exception.message_dict)

    def test_txt_without_alias(self):
        """A TXT record has no alias; its text is optional."""
        with self.assertRaises(ValidationError) as context:
            build_record(alias="a.example.net").full_clean()
        self.assertIn("alias", context.exception.message_dict)
        build_record().full_clean()

    def test_invalid_names(self):
        """Invalid record and zone names are rejected."""
        with self.assertRaises(ValidationError) as context:
            build_record(name="a..b", zone_name="").full_clean()
        self.assertIn("name", context.exception.message_dict)
        self.assertIn("zone_name", context.exception.message_dict)

    def test_unique(self):
        """The same record (type, name, zone, value) cannot be created twice."""
        build_record(text="token").validated_save()
        with self.assertRaises(ValidationError):
            build_record(text="token").validated_save()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            build_record(text="token").save()
        build_record(text="other").validated_save()

    def test_certificates(self):
        """A record can be linked to several certificates, and a certificate to several records."""
        fixtures.create_domain_validation_records()
        www = models.Certificate.objects.get(name="www.example.com 2026")
        self.assertEqual(www.domain_validation_records.count(), 2)
        delegation = models.DomainValidationRecord.objects.get(name="_acme-challenge")
        self.assertEqual(delegation.certificates.count(), 2)


class DomainValidationRecordFilterTest(TestCase):
    """Test the DomainValidationRecord and Certificate filters added for domain validation."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_domain_validation_records()

    def filter(self, params, filterset=filters.DomainValidationRecordFilterSet, queryset=None):
        """Filtered queryset."""
        if queryset is None:
            queryset = models.DomainValidationRecord.objects.all()
        return filterset(params, queryset).qs

    def test_q(self):
        """Search in names, zone, values, description and comment."""
        self.assertEqual(self.filter({"q": "acme-dns"}).count(), 2)
        self.assertEqual(self.filter({"q": "Sectigo DCV"}).count(), 1)

    def test_record_type(self):
        """Filter on the record type."""
        self.assertEqual(self.filter({"record_type": [DNSRecordTypeChoices.CNAME]}).count(), 2)

    def test_fqdn(self):
        """Exact FQDN, whatever the split between the name and the zone."""
        self.assertEqual(self.filter({"fqdn": "_ACME-challenge.edge.example.com."}).get().name, "_acme-challenge.edge")
        self.assertEqual(self.filter({"fqdn": "Example.ORG"}).get().name, "")
        self.assertEqual(self.filter({"fqdn": "unknown.example.com"}).count(), 0)
        self.assertEqual(self.filter({"fqdn": "a..b"}).count(), 0)

    def test_certificates(self):
        """Filter on the linked certificates."""
        www = models.Certificate.objects.get(name="www.example.com 2026")
        self.assertEqual(self.filter({"certificates": [www.pk]}).count(), 2)
        self.assertEqual(self.filter({"certificates": ["Wildcard edge"]}).count(), 1)
        self.assertEqual(self.filter({"has_certificates": True}).count(), 3)
        self.assertEqual(self.filter({"has_certificates": False}).count(), 1)

    def test_certificate_expires_within_days(self):
        """Records linked to a certificate expiring soon (not yet expired)."""
        self.assertEqual(self.filter({"certificate_expires_within_days": 30}).get().name, "_acme-challenge.edge")
        self.assertEqual(self.filter({"certificate_expires_within_days": 400}).count(), 3)

    def test_certificate_filters(self):
        """Certificates filtered on the DCV method and on their domain validation records."""
        queryset = models.Certificate.objects.all()
        params = {"dcv_method": ["acme-dns-01"]}
        self.assertEqual(self.filter(params, filters.CertificateFilterSet, queryset).count(), 2)
        params = {"has_domain_validation_records": True}
        self.assertEqual(self.filter(params, filters.CertificateFilterSet, queryset).count(), 3)
        delegation = models.DomainValidationRecord.objects.get(name="_acme-challenge")
        params = {"domain_validation_records": [delegation.pk]}
        self.assertEqual(self.filter(params, filters.CertificateFilterSet, queryset).count(), 2)


class WithoutDNSModelsTest(TestCase):
    """The app works without Nautobot DNS Models: the comparison is simply not available."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_domain_validation_records()

    def setUp(self):
        """Simulate the absence of Nautobot DNS Models."""
        super().setUp()
        patcher = mock.patch.object(dns_models, "is_installed", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_comparison(self):
        """No comparison, no annotation, no creation link."""
        record = models.DomainValidationRecord.objects.first()
        self.assertIsNone(dns_models.compare(record))
        self.assertIsNone(dns_models.get_record_model(record.record_type))
        self.assertIsNone(dns_models.get_create_url(record))
        queryset = models.DomainValidationRecord.objects.all()
        self.assertNotIn(dns_models.ANNOTATION, dns_models.annotate(queryset).query.annotations)

    def test_filter_ignored(self):
        """The comparison filter does not filter anything."""
        params = {"dns_models_match": [DNSModelsMatchChoices.ABSENT]}
        queryset = models.DomainValidationRecord.objects.all()
        self.assertEqual(filters.DomainValidationRecordFilterSet(params, queryset).qs.count(), 4)

    def test_filter_form_and_table(self):
        """The comparison is hidden from the filter form and the table."""
        self.assertNotIn("dns_models_match", forms.DomainValidationRecordFilterForm().fields)
        table = tables.DomainValidationRecordTable(models.DomainValidationRecord.objects.all())
        self.assertFalse(table.columns["dns_models_match"].visible)

    def test_views(self):
        """List and detail views render without the DNS Models panel."""
        self.add_permissions(
            "nautobot_ssl_manager.view_domainvalidationrecord", "nautobot_ssl_manager.view_certificate"
        )
        response = self.client.get(reverse("plugins:nautobot_ssl_manager:domainvalidationrecord_list"))
        self.assertHttpStatus(response, 200)
        record = models.DomainValidationRecord.objects.get(name="_acme-challenge")
        response = self.client.get(record.get_absolute_url())
        self.assertHttpStatus(response, 200)
        self.assertNotIn("Create in Nautobot DNS Models", response.content.decode())
        self.assertNotIn('panel-id="nautobot-dns-models"', response.content.decode())


@skipUnless(DNS_MODELS_INSTALLED, "Nautobot DNS Models is not installed")
class WithDNSModelsTest(TestCase):
    """Comparison of Domain Validation Records with Nautobot DNS Models (computed, never stored)."""

    @classmethod
    def setUpTestData(cls):
        """Create test data: DNS Models records matching (or not) the Domain Validation Records."""
        fixtures.create_domain_validation_records()
        dns_zone_model = apps.get_model(dns_models.APP_LABEL, "DNSZone")
        txt_model = apps.get_model(dns_models.APP_LABEL, "TXTRecord")
        cname_model = apps.get_model(dns_models.APP_LABEL, "CNAMERecord")
        cls.zone = dns_zone_model.objects.create(name="example.com", filename="example.com.zone")
        # Same delegation, alias with a trailing dot and another letter case.
        cls.cname = cname_model.objects.create(
            name="_acme-challenge", zone=cls.zone, alias="Example-com.acme-dns.example.net."
        )
        # Fully qualified name in DNS Models, any text (the record has none).
        txt_model.objects.create(name="_acme-challenge.edge.example.com", zone=cls.zone, text="random")
        # Apex TXT with another value.
        apex_zone = dns_zone_model.objects.create(name="example.org", filename="example.org.zone")
        txt_model.objects.create(name="", zone=apex_zone, text="other-token")
        cls.records = {
            name: models.DomainValidationRecord.objects.get(name=name)
            for name in ("_acme-challenge", "_acme-challenge.edge", "", "_acme-challenge.api")
        }
        cls.expected = {
            "_acme-challenge": DNSModelsMatchChoices.PRESENT,
            "_acme-challenge.edge": DNSModelsMatchChoices.PRESENT,
            "": DNSModelsMatchChoices.DIFFERENT,
            "_acme-challenge.api": DNSModelsMatchChoices.ABSENT,
        }

    def test_compare(self):
        """Present, different and absent records."""
        for name, expected in self.expected.items():
            with self.subTest(name=name):
                self.assertEqual(dns_models.compare(self.records[name]).state, expected)
        comparison = dns_models.compare(self.records["_acme-challenge"])
        self.assertEqual(comparison.matches, [(self.cname, True)])
        self.assertEqual(comparison.label, "Present")

    def test_annotate_same_as_compare(self):
        """The database annotation gives the same states as `compare()`."""
        annotated = dns_models.annotate(models.DomainValidationRecord.objects.all())
        self.assertEqual({record.name: record.dns_models_match for record in annotated}, self.expected)

    def test_filter(self):
        """Filter on the comparison state."""
        queryset = models.DomainValidationRecord.objects.all()
        for state, expected in (
            (DNSModelsMatchChoices.PRESENT, 2),
            (DNSModelsMatchChoices.DIFFERENT, 1),
            (DNSModelsMatchChoices.ABSENT, 1),
        ):
            with self.subTest(state=state):
                filterset = filters.DomainValidationRecordFilterSet({"dns_models_match": [state]}, queryset)
                self.assertEqual(filterset.qs.count(), expected)
        # Already annotated queryset (REST API).
        filterset = filters.DomainValidationRecordFilterSet(
            {"dns_models_match": [DNSModelsMatchChoices.ABSENT]}, dns_models.annotate(queryset)
        )
        self.assertEqual(filterset.qs.get().name, "_acme-challenge.api")

    def test_deleted_dns_models_record(self):
        """A record deleted from DNS Models is reported as absent at once (nothing stored)."""
        self.cname.delete()
        self.assertEqual(dns_models.compare(self.records["_acme-challenge"]).state, DNSModelsMatchChoices.ABSENT)

    def test_restricted_to_user(self):
        """Only the DNS Models records visible to the user are considered."""
        filterset = filters.DomainValidationRecordFilterSet(
            {"dns_models_match": [DNSModelsMatchChoices.ABSENT]},
            models.DomainValidationRecord.objects.all(),
            request=mock.Mock(user=self.user),
        )
        self.assertEqual(filterset.qs.count(), 4)
        self.assertEqual(
            dns_models.compare(self.records["_acme-challenge"], user=self.user).state, DNSModelsMatchChoices.ABSENT
        )

    def test_create_url(self):
        """Creation form of DNS Models pre-filled with the values of the record, zone selected when unique."""
        url = dns_models.get_create_url(self.records["_acme-challenge.api"])
        self.assertTrue(url.startswith(reverse("plugins:nautobot_dns_models:cnamerecord_add")))
        self.assertIn("name=_acme-challenge.api", url)
        self.assertIn(f"zone={self.zone.pk}", url)
        self.assertIn("alias=api.acme-dns.example.net", url)
        txt_url = dns_models.get_create_url(self.records[""])
        self.assertIn("text=dv-token-123", txt_url)
        self.assertIn("_ttl=3600", txt_url)

    def test_detail_view(self):
        """Detail view: comparison panel, creation link only for an absent record and with the permission."""
        self.add_permissions(
            "nautobot_ssl_manager.view_domainvalidationrecord",
            "nautobot_dns_models.view_cnamerecord",
            "nautobot_dns_models.view_dnszone",
        )
        response = self.client.get(self.records["_acme-challenge"].get_absolute_url())
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn('panel-id="nautobot-dns-models"', content)
        self.assertIn("A record with the same type, name, zone and value exists.", content)
        self.assertIn(self.cname.get_absolute_url(), content)
        response = self.client.get(self.records["_acme-challenge.api"].get_absolute_url())
        self.assertNotIn("Create in Nautobot DNS Models", response.content.decode())
        self.add_permissions("nautobot_dns_models.add_cnamerecord")
        response = self.client.get(self.records["_acme-challenge.api"].get_absolute_url())
        self.assertIn("Create in Nautobot DNS Models", response.content.decode())

    def test_list_view(self):
        """List view: comparison column (DNS Models records visible to the user only)."""
        url = reverse("plugins:nautobot_ssl_manager:domainvalidationrecord_list")
        self.add_permissions("nautobot_ssl_manager.view_domainvalidationrecord")
        # The rows of the list are loaded with HTMX.
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn('bg-danger">Absent<', content)
        self.assertNotIn('bg-success">Present<', content)
        ObjectPermission.objects.all().delete()
        self.add_permissions(
            "nautobot_ssl_manager.view_domainvalidationrecord",
            "nautobot_dns_models.view_cnamerecord",
            "nautobot_dns_models.view_txtrecord",
        )
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        content = response.content.decode()
        self.assertIn('bg-success">Present<', content)
        self.assertIn('bg-warning">Different<', content)

    def test_table_without_annotation(self):
        """Table of the records of a certificate (not annotated): state computed per row for the request user."""
        self.add_permissions("nautobot_dns_models.view_cnamerecord")
        table = tables.DomainValidationRecordTable(models.DomainValidationRecord.objects.filter(name="_acme-challenge"))
        record = self.records["_acme-challenge"]
        self.assertEqual(table.render_dns_models_match(record, None), "—")
        table.request = RequestFactory().get("/")
        table.request.user = self.user
        self.assertIn("Present", table.render_dns_models_match(record, None))
