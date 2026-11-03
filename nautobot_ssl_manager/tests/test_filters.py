"""Test filtersets for nautobot_ssl_manager."""

from nautobot.apps.testing import FilterTestCases

from nautobot_ssl_manager import filters, models
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import fixtures


class CertificateProviderFilterTestCase(  # pylint: disable=too-many-ancestors
    FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    """CertificateProvider filter test case."""

    queryset = models.CertificateProvider.objects.all()
    filterset = filters.CertificateProviderFilterSet
    tenancy_related_name = "certificate_providers"
    generic_filter_tests = (
        ("comments",),
        ("description",),
        ("name",),
        ("portal_url",),
    )

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificate_authorities()

    def test_q_search(self):
        """Search by name."""
        self.assertEqual(self.filterset({"q": "sectigo"}, self.queryset).qs.count(), 1)

    def test_q_invalid(self):
        """Search with no match."""
        self.assertEqual(self.filterset({"q": "does-not-exist"}, self.queryset).qs.count(), 0)

    def test_has_certificate_authorities(self):
        """Filter providers on whether they have CAs."""
        params = {"has_certificate_authorities": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"has_certificate_authorities": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class CertificateAuthorityFilterTestCase(  # pylint: disable=too-many-ancestors
    FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    """CertificateAuthority filter test case."""

    queryset = models.CertificateAuthority.objects.all()
    filterset = filters.CertificateAuthorityFilterSet
    tenancy_related_name = "certificate_authorities"
    generic_filter_tests = (
        ("comments",),
        ("description",),
        ("name",),
        ("provider", "provider__id"),
        ("provider", "provider__name"),
        ("status", "status__id"),
        ("status", "status__name"),
        ("portal_url",),
    )

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificate_authorities()

    def test_q_search(self):
        """Search by name."""
        self.assertEqual(self.filterset({"q": "Lab Root"}, self.queryset).qs.count(), 1)

    def test_q_invalid(self):
        """Search with no match."""
        self.assertEqual(self.filterset({"q": "does-not-exist"}, self.queryset).qs.count(), 0)

    def test_type(self):
        """Filter by type."""
        params = {"type": [CertificateAuthorityTypeChoices.TYPE_PUBLIC]}
        self.assertQuerySetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(type=CertificateAuthorityTypeChoices.TYPE_PUBLIC),
            ordered=False,
        )

    def test_has_provider(self):
        """Filter CAs on whether they have a provider."""
        self.assertEqual(self.filterset({"has_provider": True}, self.queryset).qs.count(), 3)
        self.assertEqual(self.filterset({"has_provider": False}, self.queryset).qs.count(), 1)

    def test_parent(self):
        """Filter CAs by issuer (name or ID)."""
        root = models.CertificateAuthority.objects.get(name="Lab Root CA")
        for value in (root.name, str(root.pk)):
            self.assertEqual(
                list(self.filterset({"parent": [value]}, self.queryset).qs.values_list("name", flat=True)),
                ["Internal Issuing CA"],
            )

    def test_has_parent(self):
        """Filter Intermediate CAs (with an issuer) and Root CAs (without)."""
        self.assertQuerySetEqual(
            self.filterset({"has_parent": True}, self.queryset).qs,
            self.queryset.filter(parent__isnull=False),
            ordered=False,
        )
        self.assertQuerySetEqual(
            self.filterset({"has_parent": False}, self.queryset).qs,
            self.queryset.filter(parent__isnull=True),
            ordered=False,
        )

    def test_children(self):
        """Filter CAs by the CAs they issued."""
        params = {"children": ["Internal Issuing CA"]}
        self.assertEqual(list(self.filterset(params, self.queryset).qs.values_list("name", flat=True)), ["Lab Root CA"])

    def test_has_children(self):
        """Filter CAs on whether they issued other CAs."""
        self.assertEqual(
            list(self.filterset({"has_children": True}, self.queryset).qs.values_list("name", flat=True)),
            ["Lab Root CA"],
        )
        self.assertEqual(self.filterset({"has_children": False}, self.queryset).qs.count(), 3)


class CertificateFilterTestCase(  # pylint: disable=too-many-ancestors
    FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin
):
    """Certificate filter test case."""

    queryset = models.Certificate.objects.all()
    filterset = filters.CertificateFilterSet
    tenancy_related_name = "certificates"
    generic_filter_tests = (
        ("certificate_authority", "certificate_authority__id"),
        ("certificate_authority", "certificate_authority__name"),
        ("common_name",),
        ("description",),
        ("fingerprint_sha256",),
        ("key_size",),
        ("name",),
        ("order_number",),
        ("serial_number",),
        ("status", "status__id"),
        ("status", "status__name"),
    )

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        fixtures.create_certificates()

    def test_q_search(self):
        self.assertEqual(self.filterset({"q": "edge.example"}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"q": "ORD-002"}, self.queryset).qs.count(), 1)

    def test_san(self):
        params = {"san": "WWW.example.com"}
        self.assertEqual(
            set(self.filterset(params, self.queryset).qs.values_list("name", flat=True)),
            {"www.example.com 2025", "www.example.com 2026"},
        )
        self.assertEqual(self.filterset({"san": "10.0.0.1"}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"san": "not valid"}, self.queryset).qs.count(), 0)

    def test_extended_key_usage(self):
        params = {"extended_key_usage": ["clientAuth"]}
        self.assertEqual(
            set(self.filterset(params, self.queryset).qs.values_list("name", flat=True)),
            {"www.example.com 2026", "vpn-client-01"},
        )

    def test_expired(self):
        self.assertEqual(self.filterset({"expired": True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"expired": False}, self.queryset).qs.count(), 4)

    def test_expires_within_days(self):
        self.assertEqual(
            list(self.filterset({"expires_within_days": 30}, self.queryset).qs.values_list("name", flat=True)),
            ["Wildcard edge"],
        )

    def test_auto_renew(self):
        self.assertEqual(self.filterset({"auto_renew": True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"auto_renew": False}, self.queryset).qs.count(), 2)

    def test_key_algorithm_and_validation_level(self):
        self.assertEqual(self.filterset({"key_algorithm": ["ecdsa"]}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"validation_level": ["dv"]}, self.queryset).qs.count(), 2)

    def test_provider(self):
        self.assertEqual(self.filterset({"provider": ["Sectigo"]}, self.queryset).qs.count(), 2)

    def test_replaces_and_has_replaced_by(self):
        self.assertEqual(
            list(
                self.filterset({"replaces": ["www.example.com 2025"]}, self.queryset).qs.values_list("name", flat=True)
            ),
            ["www.example.com 2026"],
        )
        self.assertEqual(self.filterset({"has_replaced_by": True}, self.queryset).qs.count(), 1)
