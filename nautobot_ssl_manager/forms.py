"""Forms for nautobot_ssl_manager."""

from django import forms
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    SmallTextarea,
    StaticSelect2,
    StaticSelect2Multiple,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagFilterField,
    TagsBulkEditFormMixin,
    add_blank_choice,
)
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant

from nautobot_ssl_manager import choices, models

#
# Certificate Providers
#


class CertificateProviderForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """CertificateProvider creation/edit form."""

    comments = CommentField()

    field_order = ["name", "description", "portal_url", "tenant_group", "tenant", "comments", "tags"]

    class Meta:
        """Meta attributes."""

        model = models.CertificateProvider
        fields = "__all__"


class CertificateProviderBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """CertificateProvider bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.CertificateProvider.objects.all(), widget=forms.MultipleHiddenInput
    )
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    portal_url = forms.URLField(required=False, label="Portal URL")
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
            "portal_url",
            "tenant",
            "comments",
        ]


class CertificateProviderFilterForm(NautobotFilterForm, TenancyFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for CertificateProvider."""

    model = models.CertificateProvider
    field_order = ["q", "name", "tenant_group", "tenant"]

    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False, label="Name")
    tags = TagFilterField(model)


#
# Certificate Authorities
#


class CertificateAuthorityForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """CertificateAuthority creation/edit form."""

    provider = DynamicModelChoiceField(queryset=models.CertificateProvider.objects.all(), required=False)
    comments = CommentField()

    field_order = [
        "name",
        "type",
        "status",
        "provider",
        "description",
        "portal_url",
        "tenant_group",
        "tenant",
        "comments",
        "tags",
    ]

    class Meta:
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = "__all__"


class CertificateAuthorityBulkEditForm(  # pylint: disable=too-many-ancestors
    TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm
):
    """CertificateAuthority bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=models.CertificateAuthority.objects.all(), widget=forms.MultipleHiddenInput
    )
    type = forms.ChoiceField(
        choices=add_blank_choice(choices.CertificateAuthorityTypeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    provider = DynamicModelChoiceField(queryset=models.CertificateProvider.objects.all(), required=False)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    portal_url = forms.URLField(required=False, label="Portal URL")
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "provider",
            "description",
            "portal_url",
            "tenant",
            "comments",
        ]


class CertificateAuthorityFilterForm(  # pylint: disable=too-many-ancestors
    NautobotFilterForm, TenancyFilterForm, StatusModelFilterFormMixin
):
    """Filter form for CertificateAuthority."""

    model = models.CertificateAuthority
    field_order = ["q", "name", "type", "status", "provider", "tenant_group", "tenant"]

    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False, label="Name")
    type = forms.MultipleChoiceField(
        choices=choices.CertificateAuthorityTypeChoices,
        required=False,
        widget=StaticSelect2Multiple(),
    )
    provider = DynamicModelMultipleChoiceField(
        queryset=models.CertificateProvider.objects.all(),
        to_field_name="name",
        required=False,
    )
    tags = TagFilterField(model)
