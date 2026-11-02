"""Unit tests for views."""

from nautobot.apps.testing import ViewTestCases

from nautobot_ssl_manager import models
from nautobot_ssl_manager.tests import fixtures


class NautobotSslManagerExampleModelViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the NautobotSslManagerExampleModel views."""

    model = models.NautobotSslManagerExampleModel
    bulk_edit_data = {"description": "Bulk edit views"}
    form_data = {
        "name": "Test 1",
        "description": "Initial model",
    }

    update_data = {
        "name": "Test 2",
        "description": "Updated model",
    }

    @classmethod
    def setUpTestData(cls):
        fixtures.create_nautobotsslmanagerexamplemodel()
