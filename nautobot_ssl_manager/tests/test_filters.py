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
