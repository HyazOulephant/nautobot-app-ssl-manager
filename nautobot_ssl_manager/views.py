"""Views for nautobot_ssl_manager."""

from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel, SectionChoices
from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.templatetags import helpers

from nautobot_ssl_manager import filters, forms, models, tables
from nautobot_ssl_manager.api import serializers


class CertificateProviderUIViewSet(NautobotUIViewSet):
    """ViewSet for CertificateProvider views."""

    bulk_update_form_class = forms.CertificateProviderBulkEditForm
    filterset_class = filters.CertificateProviderFilterSet
    filterset_form_class = forms.CertificateProviderFilterForm
    form_class = forms.CertificateProviderForm
    lookup_field = "pk"
    queryset = models.CertificateProvider.objects.all()
    serializer_class = serializers.CertificateProviderSerializer
    table_class = tables.CertificateProviderTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["name", "description", "portal_url", "tenant"],
                value_transforms={"portal_url": [helpers.hyperlinked_field]},
            ),
            ObjectsTablePanel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.CertificateAuthorityTable,
                table_filter="provider",
                exclude_columns=["provider"],
            ),
        ],
    )


class CertificateAuthorityUIViewSet(NautobotUIViewSet):
    """ViewSet for CertificateAuthority views."""

    bulk_update_form_class = forms.CertificateAuthorityBulkEditForm
    filterset_class = filters.CertificateAuthorityFilterSet
    filterset_form_class = forms.CertificateAuthorityFilterForm
    form_class = forms.CertificateAuthorityForm
    lookup_field = "pk"
    queryset = models.CertificateAuthority.objects.all()
    serializer_class = serializers.CertificateAuthoritySerializer
    table_class = tables.CertificateAuthorityTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["name", "type", "status", "provider", "description", "portal_url", "tenant"],
                value_transforms={"portal_url": [helpers.hyperlinked_field]},
            ),
        ],
    )
