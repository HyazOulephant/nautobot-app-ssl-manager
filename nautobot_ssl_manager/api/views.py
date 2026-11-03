"""API views for nautobot_ssl_manager."""

from nautobot.apps.api import NautobotModelViewSet

from nautobot_ssl_manager import filters, models
from nautobot_ssl_manager.api import serializers


class CertificateProviderViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """CertificateProvider viewset."""

    queryset = models.CertificateProvider.objects.all()
    serializer_class = serializers.CertificateProviderSerializer
    filterset_class = filters.CertificateProviderFilterSet


class CertificateAuthorityViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """CertificateAuthority viewset."""

    queryset = models.CertificateAuthority.objects.all()
    serializer_class = serializers.CertificateAuthoritySerializer
    filterset_class = filters.CertificateAuthorityFilterSet


class CertificateViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """Certificate viewset."""

    queryset = models.Certificate.objects.all()
    serializer_class = serializers.CertificateSerializer
    filterset_class = filters.CertificateFilterSet
