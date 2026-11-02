"""Test NautobotSslManagerExampleModel."""

from nautobot.apps.testing import ModelTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.tests import fixtures


class TestNautobotSslManagerExampleModel(ModelTestCases.BaseModelTestCase):
    """Test NautobotSslManagerExampleModel."""

    model = models.NautobotSslManagerExampleModel

    @classmethod
    def setUpTestData(cls):
        """Create test data for NautobotSslManagerExampleModel Model."""
        super().setUpTestData()
        # Create 3 objects for the model test cases.
        fixtures.create_nautobotsslmanagerexamplemodel()

    def test_create_nautobotsslmanagerexamplemodel_only_required(self):
        """Create with only required fields, and validate null description and __str__."""
        nautobotsslmanagerexamplemodel = models.NautobotSslManagerExampleModel.objects.create(name="Development")
        self.assertEqual(nautobotsslmanagerexamplemodel.name, "Development")
        self.assertEqual(nautobotsslmanagerexamplemodel.description, "")
        self.assertEqual(str(nautobotsslmanagerexamplemodel), "Development")

    def test_create_nautobotsslmanagerexamplemodel_all_fields_success(self):
        """Create NautobotSslManagerExampleModel with all fields."""
        nautobotsslmanagerexamplemodel = models.NautobotSslManagerExampleModel.objects.create(
            name="Development", description="Development Test"
        )
        self.assertEqual(nautobotsslmanagerexamplemodel.name, "Development")
        self.assertEqual(nautobotsslmanagerexamplemodel.description, "Development Test")
