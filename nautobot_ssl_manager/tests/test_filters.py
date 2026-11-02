"""Test NautobotSslManagerExampleModel Filter."""

from nautobot.apps.testing import FilterTestCases

from nautobot_ssl_manager import filters, models
from nautobot_ssl_manager.tests import fixtures


class NautobotSslManagerExampleModelFilterTestCase(FilterTestCases.FilterTestCase):  # pylint: disable=too-many-ancestors
    """NautobotSslManagerExampleModel Filter Test Case."""

    queryset = models.NautobotSslManagerExampleModel.objects.all()
    filterset = filters.NautobotSslManagerExampleModelFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        """Setup test data for NautobotSslManagerExampleModel Model."""
        fixtures.create_nautobotsslmanagerexamplemodel()

    def test_q_search_name(self):
        """Test using Q search with name of NautobotSslManagerExampleModel."""
        params = {"q": "Test One"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_q_invalid(self):
        """Test using invalid Q search for NautobotSslManagerExampleModel."""
        params = {"q": "test-five"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
