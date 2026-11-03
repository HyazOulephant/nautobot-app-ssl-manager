"""Forms for nautobot_ssl_manager."""

from django import forms
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import (
    BulkEditNullBooleanSelect,
    CommentField,
    DateTimePicker,
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
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant

from nautobot_ssl_manager import choices, models, utils

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

    parent = DynamicModelChoiceField(
        queryset=models.CertificateAuthority.objects.all(),
        required=False,
        label="Issued by",
        help_text="CA that issued this CA's certificate. Leave empty for a Root CA.",
    )
    provider = DynamicModelChoiceField(queryset=models.CertificateProvider.objects.all(), required=False)
    comments = CommentField()

    field_order = [
        "name",
        "parent",
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

    def __init__(self, *args, **kwargs):
        """A CA cannot be issued by itself or by one of the CAs it issued."""
        super().__init__(*args, **kwargs)
        if self.instance.present_in_database:
            self.fields["parent"].queryset = models.CertificateAuthority.objects.exclude(
                pk__in=self.instance.descendants(include_self=True).values("pk")
            )


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
    parent = DynamicModelChoiceField(
        queryset=models.CertificateAuthority.objects.all(), required=False, label="Issued by"
    )
    provider = DynamicModelChoiceField(queryset=models.CertificateProvider.objects.all(), required=False)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    portal_url = forms.URLField(required=False, label="Portal URL")
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "parent",
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
    field_order = ["q", "name", "parent", "has_parent", "type", "status", "provider", "tenant_group", "tenant"]

    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False, label="Name")
    parent = DynamicModelMultipleChoiceField(
        queryset=models.CertificateAuthority.objects.all(),
        to_field_name="name",
        required=False,
        label="Issued by",
    )
    has_parent = forms.NullBooleanField(
        required=False,
        label="Intermediate CA",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
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


#
# Certificates
#

AUTO_RENEW_CHOICES = (
    ("", "Unknown"),
    ("True", "Yes"),
    ("False", "No"),
)


class SubjectAlternativeNamesWidget(forms.Textarea):
    """Textarea accepting either one multi-line value or several values (e.g. API-like form posts)."""

    def value_from_datadict(self, data, files, name):
        """Join several submitted values into one multi-line value."""
        if hasattr(data, "getlist"):
            values = data.getlist(name)
            if len(values) > 1:
                return "\n".join(values)
        return super().value_from_datadict(data, files, name)


class SubjectAlternativeNamesField(forms.CharField):
    """Textarea field editing a list of SANs, one entry per line."""

    widget = SubjectAlternativeNamesWidget(attrs={"rows": 5, "placeholder": "www.example.com\n*.example.com\n10.0.0.1"})

    def __init__(self, **kwargs):
        """Set field defaults."""
        kwargs.setdefault("required", False)
        kwargs.setdefault("label", "Subject Alternative Names")
        kwargs.setdefault(
            "help_text",
            "One entry per line: DNS names (wildcards allowed) and IP addresses. "
            "Other types are prefixed with <code>email:</code> or <code>uri:</code>.",
        )
        super().__init__(**kwargs)

    def prepare_value(self, value):
        """Render a list as one entry per line."""
        if isinstance(value, (list, tuple)):
            return "\n".join(str(entry) for entry in value)
        return value

    def to_python(self, value):
        """Convert the textarea content to a list of normalized SANs."""
        if isinstance(value, (list, tuple)):
            lines = list(value)
        else:
            text = "" if value in self.empty_values else str(value)
            lines = text.replace(",", "\n").splitlines()
        try:
            return utils.normalize_san_list(lines)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


class CertificateForm(NautobotModelForm, TenancyForm):  # pylint: disable=too-many-ancestors
    """Certificate creation/edit form."""

    subject_alternative_names = SubjectAlternativeNamesField()
    certificate_authority = DynamicModelChoiceField(
        queryset=models.CertificateAuthority.objects.all(), required=False, label="Certificate Authority"
    )
    replaces = DynamicModelChoiceField(
        queryset=models.Certificate.objects.all(),
        required=False,
        help_text="Previous certificate replaced by this one (renewal)",
    )
    extended_key_usage = forms.MultipleChoiceField(
        choices=choices.ExtendedKeyUsageChoices,
        required=False,
        widget=StaticSelect2Multiple(),
        label="Extended Key Usage",
    )
    auto_renew = forms.NullBooleanField(
        required=False,
        widget=StaticSelect2(choices=AUTO_RENEW_CHOICES),
        label="Auto-renew",
        help_text="Leave Unknown if not confirmed",
    )
    pem = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "class": "font-monospace"}),
        label="PEM",
        help_text="Public certificate only. Private keys are rejected.",
    )
    comments = CommentField()

    field_order = [
        "name",
        "common_name",
        "subject_alternative_names",
        "status",
        "certificate_authority",
        "not_before",
        "not_after",
        "replaces",
        "auto_renew",
        "order_number",
        "key_algorithm",
        "key_size",
        "extended_key_usage",
        "validation_level",
        "serial_number",
        "fingerprint_sha256",
        "pem",
        "description",
        "tenant_group",
        "tenant",
        "comments",
        "tags",
    ]

    class Meta:
        """Meta attributes."""

        model = models.Certificate
        fields = "__all__"
        widgets = {
            "not_before": DateTimePicker(),
            "not_after": DateTimePicker(),
        }

    def __init__(self, *args, replaces_suggestions=None, **kwargs):
        """Optionally display suggested certificates for the `replaces` field (never selected automatically)."""
        super().__init__(*args, **kwargs)
        if self.instance.present_in_database:
            self.fields["replaces"].queryset = models.Certificate.objects.exclude(pk=self.instance.pk)
        if replaces_suggestions:
            names = ", ".join(str(certificate) for certificate in replaces_suggestions)
            self.fields[
                "replaces"
            ].help_text = (
                f"Previous certificate replaced by this one (renewal). Suggestions (same CN or shared SANs): {names}"
            )


class CertificateBulkEditForm(  # pylint: disable=too-many-ancestors
    TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm
):
    """Certificate bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.Certificate.objects.all(), widget=forms.MultipleHiddenInput)
    certificate_authority = DynamicModelChoiceField(
        queryset=models.CertificateAuthority.objects.all(), required=False, label="Certificate Authority"
    )
    auto_renew = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect, label="Auto-renew")
    validation_level = forms.ChoiceField(
        choices=add_blank_choice(choices.ValidationLevelChoices), required=False, widget=StaticSelect2()
    )
    order_number = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "certificate_authority",
            "auto_renew",
            "validation_level",
            "order_number",
            "description",
            "tenant",
            "comments",
        ]


class CertificateFilterForm(  # pylint: disable=too-many-ancestors
    NautobotFilterForm, TenancyFilterForm, StatusModelFilterFormMixin
):
    """Filter form for Certificate."""

    model = models.Certificate
    field_order = [
        "q",
        "common_name",
        "san",
        "status",
        "certificate_authority",
        "expired",
        "auto_renew",
        "validation_level",
        "key_algorithm",
        "extended_key_usage",
        "tenant_group",
        "tenant",
    ]

    q = forms.CharField(required=False, label="Search")
    common_name = forms.CharField(required=False, label="Common Name")
    san = forms.CharField(required=False, label="SAN (exact entry)")
    certificate_authority = DynamicModelMultipleChoiceField(
        queryset=models.CertificateAuthority.objects.all(),
        to_field_name="name",
        required=False,
        label="Certificate Authority",
    )
    expired = forms.NullBooleanField(
        required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES), label="Expired"
    )
    auto_renew = forms.NullBooleanField(
        required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES), label="Auto-renew"
    )
    validation_level = forms.MultipleChoiceField(
        choices=choices.ValidationLevelChoices, required=False, widget=StaticSelect2Multiple()
    )
    key_algorithm = forms.MultipleChoiceField(
        choices=choices.KeyAlgorithmChoices, required=False, widget=StaticSelect2Multiple()
    )
    extended_key_usage = forms.MultipleChoiceField(
        choices=choices.ExtendedKeyUsageChoices,
        required=False,
        widget=StaticSelect2Multiple(),
        label="Extended Key Usage",
    )
    tags = TagFilterField(model)


class CertificateImportPEMForm(forms.Form):  # pylint: disable=nb-incorrect-base-class
    """Paste a PEM certificate to pre-fill a new Certificate."""

    pem = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 14,
                "class": "font-monospace",
                "placeholder": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            }
        ),
        label="PEM certificate",
        help_text="Public certificate only. Private keys are rejected and never stored.",
    )

    def clean_pem(self):
        """Parse the PEM and reject duplicates."""
        try:
            parsed = utils.parse_pem_certificate(self.cleaned_data["pem"])
        except utils.CertificateParseError as exc:
            raise forms.ValidationError(str(exc)) from exc
        existing = models.Certificate.objects.filter(fingerprint_sha256=parsed.fingerprint_sha256).first()
        if existing:
            raise forms.ValidationError(f"This certificate already exists in Nautobot: {existing}.")
        self.parsed = parsed  # pylint: disable=attribute-defined-outside-init
        return parsed.pem
