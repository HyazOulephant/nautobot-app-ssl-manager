"""Views for nautobot_ssl_manager."""

from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, SectionChoices
from nautobot.apps.views import NautobotUIViewSet

from nautobot_ssl_manager import filters, forms, models, tables
from nautobot_ssl_manager.api import serializers


class NautobotSslManagerExampleModelUIViewSet(NautobotUIViewSet):
    """ViewSet for NautobotSslManagerExampleModel views."""

    bulk_update_form_class = forms.NautobotSslManagerExampleModelBulkEditForm
    filterset_class = filters.NautobotSslManagerExampleModelFilterSet
    filterset_form_class = forms.NautobotSslManagerExampleModelFilterForm
    form_class = forms.NautobotSslManagerExampleModelForm
    lookup_field = "pk"
    queryset = models.NautobotSslManagerExampleModel.objects.all()
    serializer_class = serializers.NautobotSslManagerExampleModelSerializer
    table_class = tables.NautobotSslManagerExampleModelTable

    # Here is an example of using the UI  Component Framework for the detail view.
    # More information can be found in the Nautobot documentation:
    # https://docs.nautobot.com/projects/core/en/stable/development/core/ui-component-framework/
    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                # Alternatively, you can specify a list of field names:
                # fields=[
                #     "name",
                #     "description",
                # ],
                # Some fields may require additional configuration, we can use value_transforms
                # value_transforms={
                #     "name": [helpers.bettertitle]
                # },
            ),
            # If there is a ForeignKey or M2M with this model we can use ObjectsTablePanel
            # to display them in a table format.
            # ObjectsTablePanel(
            # weight=200,
            # section=SectionChoices.RIGHT_HALF,
            # table_class=tables.NautobotSslManagerExampleModelTable,
            # You will want to filter the table using the related_name
            # filter="nautobotsslmanagerexamplemodels",
            # ),
        ],
    )
