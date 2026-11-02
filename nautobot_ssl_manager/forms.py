"""Forms for nautobot_ssl_manager."""

from django import forms
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin

from nautobot_ssl_manager import models


class NautobotSslManagerExampleModelForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """NautobotSslManagerExampleModel creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.NautobotSslManagerExampleModel
        fields = "__all__"


class NautobotSslManagerExampleModelBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """NautobotSslManagerExampleModel bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.NautobotSslManagerExampleModel.objects.all(), widget=forms.MultipleHiddenInput
    )
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
        ]


class NautobotSslManagerExampleModelFilterForm(NautobotFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form to filter searches."""

    model = models.NautobotSslManagerExampleModel
    field_order = ["q", "name"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name.",
    )
    name = forms.CharField(required=False, label="Name")
