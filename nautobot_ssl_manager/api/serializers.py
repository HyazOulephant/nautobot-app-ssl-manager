"""API serializers for nautobot_ssl_manager."""

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from nautobot_ssl_manager import models


class CertificateProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """CertificateProvider Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.CertificateProvider
        fields = "__all__"


class CertificateAuthoritySerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """CertificateAuthority Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = "__all__"
