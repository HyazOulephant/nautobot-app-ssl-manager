"""Filtering for nautobot_ssl_manager."""

from nautobot.apps.filters import NameSearchFilterSet, NautobotFilterSet

from nautobot_ssl_manager import models


class NautobotSslManagerExampleModelFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for NautobotSslManagerExampleModel."""

    class Meta:
        """Meta attributes for filter."""

        model = models.NautobotSslManagerExampleModel

        # add any fields from the model that you would like to filter your searches by using those
        fields = "__all__"
