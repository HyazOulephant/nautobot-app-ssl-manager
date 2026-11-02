"""Create fixtures for tests."""

from nautobot_ssl_manager.models import NautobotSslManagerExampleModel


def create_nautobotsslmanagerexamplemodel():
    """Fixture to create necessary number of NautobotSslManagerExampleModel for tests."""
    NautobotSslManagerExampleModel.objects.create(name="Test One")
    NautobotSslManagerExampleModel.objects.create(name="Test Two")
    NautobotSslManagerExampleModel.objects.create(name="Test Three")
