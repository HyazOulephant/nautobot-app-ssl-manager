"""Test nautobotsslmanagerexamplemodel forms."""

from django.test import TestCase

from nautobot_ssl_manager import forms


class NautobotSslManagerExampleModelTest(TestCase):
    """Test NautobotSslManagerExampleModel forms."""

    def test_specifying_all_fields_success(self):
        form = forms.NautobotSslManagerExampleModelForm(
            data={
                "name": "Development",
                "description": "Development Testing",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_only_required_success(self):
        form = forms.NautobotSslManagerExampleModelForm(
            data={
                "name": "Development",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_name_nautobotsslmanagerexamplemodel_is_required(self):
        form = forms.NautobotSslManagerExampleModelForm(data={"description": "Development Testing"})
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])
