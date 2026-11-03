"""API serializers for nautobot_ssl_manager."""

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin, TreeModelSerializerMixin
from rest_framework import serializers

from nautobot_ssl_manager import models


class CertificateProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """CertificateProvider Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.CertificateProvider
        fields = "__all__"


class CertificateAuthoritySerializer(  # pylint: disable=too-many-ancestors
    NautobotModelSerializer, TaggedModelSerializerMixin, TreeModelSerializerMixin
):
    """CertificateAuthority Serializer."""

    chain_role = serializers.CharField(read_only=True)

    class Meta:
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = "__all__"


class CertificateSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """Certificate Serializer."""

    days_remaining = serializers.IntegerField(read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True, allow_null=True)
    is_wildcard = serializers.BooleanField(read_only=True)

    class Meta:
        """Meta attributes."""

        model = models.Certificate
        fields = "__all__"
