"""API views for nautobot_ssl_manager."""

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from nautobot.apps.api import NautobotModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot_ssl_manager import downloads, filters, models
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

    @extend_schema(
        filters=False,
        parameters=[
            OpenApiParameter(
                name="file_format",
                location="query",
                required=False,
                type=OpenApiTypes.STR,
                enum=list(downloads.FORMATS),
                description="pem (default), der (single certificate only) or p7b (PKCS#7, DER encoded)",
            ),
            OpenApiParameter(
                name="chain",
                location="query",
                required=False,
                type=OpenApiTypes.BOOL,
                description="Append the CA certificates of the chain (issuing CA first)",
            ),
            OpenApiParameter(
                name="include_root",
                location="query",
                required=False,
                type=OpenApiTypes.BOOL,
                description="With chain: also include the self-signed Root CA certificate",
            ),
        ],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Certificate file (attachment)"),
            400: OpenApiResponse(description="The file cannot be built (no PEM, incomplete or inconsistent chain)"),
            403: OpenApiResponse(description="A Certificate Authority or certificate of the chain is not visible"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Download the public certificate, optionally with its chain."""
        # Not `get_object()`: its strict filtering would reject the download parameters as unknown filters.
        certificate = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            download = downloads.build_download(
                certificate,
                file_format=request.query_params.get("file_format"),
                chain=downloads.parse_bool(request.query_params.get("chain")),
                include_root=downloads.parse_bool(request.query_params.get("include_root")),
                user=request.user,
            )
        except downloads.CertificateDownloadPermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except downloads.CertificateDownloadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return downloads.download_response(download)
