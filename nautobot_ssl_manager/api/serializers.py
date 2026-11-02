"""API serializers for nautobot_ssl_manager."""

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from nautobot_ssl_manager import models


class NautobotSslManagerExampleModelSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """NautobotSslManagerExampleModel Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.NautobotSslManagerExampleModel
        fields = "__all__"

        # Option for disabling write for certain fields:
        # read_only_fields = []
