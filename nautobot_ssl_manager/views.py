"""Views for nautobot_ssl_manager."""

from uuid import uuid4

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from nautobot.apps.ui import (
    BaseTextPanel,
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    ObjectTextPanel,
    Panel,
    SectionChoices,
)
from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.forms.utils import restrict_form_fields
from nautobot.core.templatetags import helpers
from nautobot.core.views.utils import get_obj_from_context
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot_ssl_manager import choices, filters, forms, models, tables
from nautobot_ssl_manager.api import serializers


class CertificationChainPanel(Panel):
    """Certification chain from the Root CA down to the displayed object (Certificate or Certificate Authority)."""

    body_content_template_path = "nautobot_ssl_manager/inc/certification_chain.html"
    label = "Certification chain"

    def get_extra_context(self, context):
        """Build the chain nodes, Root CA first."""
        obj = get_obj_from_context(context)
        if isinstance(obj, models.Certificate):
            issuers = obj.chain
            nodes = []
            if issuers:
                nodes = [self._ca_node(ca) for ca in reversed(issuers)]
                nodes.append(
                    {"object": obj, "role": "Certificate", "icon": "mdi-file-certificate-outline", "is_current": True}
                )
        else:
            nodes = [self._ca_node(ca, is_current=ca.pk == obj.pk) for ca in reversed(obj.chain)]
        return {**super().get_extra_context(context), "chain_nodes": nodes}

    @staticmethod
    def _ca_node(ca, is_current=False):
        icon = "mdi-shield-lock-outline" if ca.chain_role == ca.ROLE_ROOT else "mdi-shield-check-outline"
        return {"object": ca, "role": f"{ca.chain_role} CA", "icon": icon, "is_current": is_current}


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
                fields=[
                    "name",
                    "type",
                    "status",
                    "parent",
                    "chain_role",
                    "certificate",
                    "certificate__not_after",
                    "certificate__days_remaining",
                    "provider",
                    "tenant",
                    "description",
                    "portal_url",
                ],
                key_transforms={
                    "chain_role": "Role",
                    "certificate__not_after": "CA certificate expires",
                    "certificate__days_remaining": "Days remaining",
                },
                value_transforms={"portal_url": [helpers.hyperlinked_field]},
            ),
            CertificationChainPanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
            ),
            ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.CertificateAuthorityTable,
                table_filter="parent",
                table_title="Issued Certificate Authorities",
                exclude_columns=["parent"],
                # Direct children only: no tree indentation needed, and avoids recursive queries on Nautobot < 3.2.
                hide_hierarchy_ui=True,
            ),
            ObjectsTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.CertificateTable,
                table_filter="certificate_authority",
                table_title="Issued Certificates",
                exclude_columns=["certificate_authority"],
            ),
        ],
    )


PEM_IMPORT_SESSION_KEY = "nautobot_ssl_manager_pem_import"
PEM_IMPORT_SESSION_MAX_ENTRIES = 5
REPLACES_SUGGESTIONS_LIMIT = 5


def render_list(value):
    """Render a list of strings, one per line."""
    if not value:
        return helpers.placeholder(None)
    # Inline rendering: Nautobot wraps the value in a <span> followed by an inline copy button,
    # so block elements would push that button onto an extra line.
    first, *others = value
    return format_html("<code>{}</code>", first) + format_html_join("", "<br><code>{}</code>", ((e,) for e in others))


def render_eku(value):
    """Render Extended Key Usage values with their RFC 5280 labels."""
    labels = dict(choices.ExtendedKeyUsageChoices.CHOICES)
    return render_list([labels.get(entry, entry) for entry in value or []])


def _format_datetime_for_form(value):
    """Format an aware datetime in the current timezone, as expected by the form date-time inputs."""
    if value is None:
        return None
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def build_initial_from_pem(parsed):
    """Build the Certificate form initial data from a `ParsedCertificate` (only facts read from the PEM)."""
    initial = {
        "name": parsed.common_name or (parsed.subject_alternative_names[0] if parsed.subject_alternative_names else ""),
        "common_name": parsed.common_name,
        "subject_alternative_names": parsed.subject_alternative_names,
        "serial_number": parsed.serial_number,
        "fingerprint_sha256": parsed.fingerprint_sha256,
        "not_before": _format_datetime_for_form(parsed.not_before),
        "not_after": _format_datetime_for_form(parsed.not_after),
        "key_algorithm": parsed.key_algorithm,
        "key_size": parsed.key_size,
        "validation_level": parsed.validation_level,
        "extended_key_usage": parsed.extended_key_usage,
        "pem": parsed.pem,
    }
    # Only propose a Certificate Authority on an exact, unambiguous name match.
    if parsed.issuer_common_name:
        authorities = list(models.CertificateAuthority.objects.filter(name=parsed.issuer_common_name)[:2])
        if len(authorities) == 1:
            initial["certificate_authority"] = str(authorities[0].pk)
    return {key: value for key, value in initial.items() if value not in (None, "", [])}


def get_replaces_suggestions(common_name, subject_alternative_names, exclude_fingerprint=None):
    """Certificates not yet replaced, sharing the CN or at least one SAN. Never selected automatically."""
    query = Q()
    if common_name:
        query |= Q(common_name__iexact=common_name)
    for san in (subject_alternative_names or [])[:50]:
        query |= Q(subject_alternative_names__contains=[san])
    if not query:
        return []
    queryset = models.Certificate.objects.filter(query).filter(replaced_by__isnull=True)
    if exclude_fingerprint:
        queryset = queryset.exclude(fingerprint_sha256=exclude_fingerprint)
    return list(queryset.order_by("-not_after")[:REPLACES_SUGGESTIONS_LIMIT])


def get_ca_certificate_hint(parsed):
    """Hint displayed when importing a CA certificate. The CA is only suggested, never linked automatically."""
    hint = "This is a CA certificate: once saved, link it to its Certificate Authority (CA certificate field)."
    if parsed.common_name:
        authorities = list(
            models.CertificateAuthority.objects.filter(name__iexact=parsed.common_name, certificate__isnull=True)[:2]
        )
        if len(authorities) == 1:
            hint += f" Suggested Certificate Authority (same name as the Common Name): {authorities[0]}."
    return hint


class CertificateUIViewSet(NautobotUIViewSet):
    """ViewSet for Certificate views."""

    bulk_update_form_class = forms.CertificateBulkEditForm
    filterset_class = filters.CertificateFilterSet
    filterset_form_class = forms.CertificateFilterForm
    form_class = forms.CertificateForm
    lookup_field = "pk"
    queryset = models.Certificate.objects.all()
    serializer_class = serializers.CertificateSerializer
    table_class = tables.CertificateTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                label="Certificate",
                fields=[
                    "name",
                    "common_name",
                    "status",
                    "certificate_authority",
                    "certificate_authority__provider",
                    "ca_certificate_authority",
                    "tenant",
                    "description",
                ],
                key_transforms={
                    "certificate_authority__provider": "Provider",
                    "ca_certificate_authority": "CA certificate of",
                },
            ),
            ObjectFieldsPanel(
                weight=200,
                section=SectionChoices.LEFT_HALF,
                label="Validity",
                fields=[
                    "not_before",
                    "not_after",
                    "days_remaining",
                    "is_expired",
                    "auto_renew",
                    "order_number",
                    "replaces",
                ],
                key_transforms={"days_remaining": "Days remaining", "is_expired": "Expired"},
            ),
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                label="Subject Alternative Names",
                fields=["subject_alternative_names", "is_wildcard"],
                key_transforms={"subject_alternative_names": "SANs", "is_wildcard": "Wildcard"},
                value_transforms={"subject_alternative_names": [render_list]},
            ),
            CertificationChainPanel(
                weight=150,
                section=SectionChoices.RIGHT_HALF,
            ),
            ObjectFieldsPanel(
                weight=200,
                section=SectionChoices.RIGHT_HALF,
                label="Technical details",
                fields=[
                    "validation_level",
                    "extended_key_usage",
                    "key_algorithm",
                    "key_size",
                    "serial_number",
                    "fingerprint_sha256",
                ],
                value_transforms={"extended_key_usage": [render_eku]},
            ),
            ObjectsTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.CertificateTable,
                table_filter="replaces",
                table_title="Replaced by",
                exclude_columns=["replaces"],
            ),
            ObjectTextPanel(
                weight=400,
                section=SectionChoices.FULL_WIDTH,
                label="PEM",
                object_field="pem",
                render_as=BaseTextPanel.RenderOptions.CODE,
            ),
        ],
    )

    def create(self, request, *args, **kwargs):
        """Pre-fill the creation form from a previously parsed PEM (see `import_pem`)."""
        token = request.GET.get("pem_import")
        if request.method == "GET" and token:
            initial = request.session.get(PEM_IMPORT_SESSION_KEY, {}).get(token)
            if initial:
                suggestions = get_replaces_suggestions(
                    initial.get("common_name"),
                    initial.get("subject_alternative_names"),
                    exclude_fingerprint=initial.get("fingerprint_sha256"),
                )
                form = self.get_form_class()(
                    instance=self.get_object(), initial=initial, replaces_suggestions=suggestions
                )
                restrict_form_fields(form, request.user)
                return Response({"form": form})
            messages.warning(request, "The PEM import has expired, please import the certificate again.")
        return super().create(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["GET", "POST"],
        url_path="import-pem",
        url_name="import_pem",
        custom_view_base_action="add",
    )
    def import_pem(self, request, *args, **kwargs):
        """Paste a PEM certificate, then continue on the pre-filled creation form."""
        form = forms.CertificateImportPEMForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            parsed = form.parsed
            for warning in parsed.warnings:
                messages.warning(request, warning)
            if parsed.is_ca:
                messages.info(request, get_ca_certificate_hint(parsed))
            pending = request.session.get(PEM_IMPORT_SESSION_KEY, {})
            # Keep only the most recent imports to bound the session size.
            pending = dict(list(pending.items())[-(PEM_IMPORT_SESSION_MAX_ENTRIES - 1) :])
            token = uuid4().hex
            pending[token] = build_initial_from_pem(parsed)
            request.session[PEM_IMPORT_SESSION_KEY] = pending
            return redirect(f"{reverse('plugins:nautobot_ssl_manager:certificate_add')}?pem_import={token}")
        return Response({"form": form})
