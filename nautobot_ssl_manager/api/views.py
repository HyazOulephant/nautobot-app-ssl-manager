"""API views for nautobot_ssl_manager."""

from nautobot.apps.api import NautobotModelViewSet

from nautobot_ssl_manager import filters, models
from nautobot_ssl_manager.api import serializers


class NautobotSslManagerExampleModelViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """NautobotSslManagerExampleModel viewset."""

    queryset = models.NautobotSslManagerExampleModel.objects.all()
    serializer_class = serializers.NautobotSslManagerExampleModelSerializer
    filterset_class = filters.NautobotSslManagerExampleModelFilterSet

    # Option for modifying the default HTTP methods:
    # http_method_names = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]
