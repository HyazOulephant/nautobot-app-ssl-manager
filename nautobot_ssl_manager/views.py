"""Views for nautobot_ssl_manager."""

from uuid import uuid4

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.http import urlencode
from nautobot.apps.ui import (
    BaseTextPanel,
    Button,
    DropdownButton,
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

from nautobot_ssl_manager import bundles, choices, downloads, filters, forms, issuers, models, tables, utils
from nautobot_ssl_manager.api import serializers


class CertificationChainPanel(Panel):
    """Certification chain from the Root CA down to the displayed object (Certificate or Certificate Authority).

    Each CA of the chain is displayed with its own CA certificate (or a warning when none is linked), so that the
    chain of certificates is visible, not only the CA tree. A certificate that is the CA certificate of a CA is
    displayed under that CA (it is not an extra level of the chain).
    """

    body_content_template_path = "nautobot_ssl_manager/inc/certification_chain.html"
    label = "Certification chain"

    def get_extra_context(self, context):
        """Build the chain nodes, Root CA first."""
        obj = get_obj_from_context(context)
        nodes = []
        if isinstance(obj, models.Certificate):
            authority = obj.ca_certificate_authority
            if authority is not None:
                nodes = [self._ca_node(ca, current_certificate=obj) for ca in reversed(authority.chain)]
            elif obj.chain:
                nodes = [self._ca_node(ca) for ca in reversed(obj.chain)]
                nodes.append(
                    {
                        "object": obj,
                        "role": "Certificate",
                        "icon": "mdi-file-certificate-outline",
                        "is_current": True,
                        "certificate": obj,
                        "certificate_is_current": True,
                        "is_leaf": True,
                    }
                )
        else:
            nodes = [self._ca_node(ca, is_current=ca.pk == obj.pk) for ca in reversed(obj.chain)]
        return {**super().get_extra_context(context), "chain_nodes": nodes}

    @staticmethod
    def _ca_node(ca, is_current=False, current_certificate=None):
        icon = "mdi-shield-lock-outline" if ca.chain_role == ca.ROLE_ROOT else "mdi-shield-check-outline"
        is_ca_of_current = current_certificate is not None and ca.certificate_id == current_certificate.pk
        return {
            "object": ca,
            "role": f"{ca.chain_role} CA",
            "icon": icon,
            "is_current": is_current or is_ca_of_current,
            "certificate": ca.certificate,
            "certificate_is_current": is_ca_of_current,
            "is_leaf": False,
        }


class CertificateDownloadButton(Button):
    """Entry of the Download menu: links to the download view, disabled (with the reason) when not available."""

    def __init__(self, *, file_format, chain=False, include_root=False, **kwargs):
        """Store the download parameters."""
        self.file_format = file_format
        self.chain = chain
        self.include_root = include_root
        super().__init__(link_name="plugins:nautobot_ssl_manager:certificate_download", **kwargs)

    def get_link(self, context):
        """Download URL with its query parameters."""
        params = {"file_format": self.file_format}
        if self.chain:
            params["chain"] = "true"
        if self.include_root:
            params["include_root"] = "true"
        return f"{super().get_link(context)}?{urlencode(params)}"

    def get_extra_context(self, context):
        """Disable the entry with the reason when the file cannot be built."""
        extra_context = super().get_extra_context(context)
        obj = get_obj_from_context(context, self.context_object_key)
        if self.chain:
            reason = downloads.chain_unavailable_reason(obj)
        else:
            reason = None if obj.pem else "No PEM is stored for this certificate."
        if reason:
            extra_context["attributes"] = {"disabled": "disabled", "aria-disabled": "true", "title": reason}
        return extra_context


def _download_buttons():
    chain_permissions = [
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.view_certificateauthority",
    ]
    return [
        CertificateDownloadButton(label="Certificate (PEM)", file_format=downloads.FORMAT_PEM, weight=100),
        CertificateDownloadButton(label="Certificate (DER)", file_format=downloads.FORMAT_DER, weight=200),
        CertificateDownloadButton(
            label="Certificate + chain (PEM)",
            file_format=downloads.FORMAT_PEM,
            chain=True,
            required_permissions=chain_permissions,
            weight=300,
        ),
        CertificateDownloadButton(
            label="Certificate + chain + root (PEM)",
            file_format=downloads.FORMAT_PEM,
            chain=True,
            include_root=True,
            required_permissions=chain_permissions,
            weight=400,
        ),
        CertificateDownloadButton(
            label="Certificate + chain + root (PKCS#7)",
            file_format=downloads.FORMAT_P7B,
            chain=True,
            include_root=True,
            required_permissions=chain_permissions,
            weight=500,
        ),
    ]


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


ISSUER_SESSION_KEY = "_issuer"


def build_initial_from_pem(parsed, identification=None):
    """Build the Certificate form initial data from a `ParsedCertificate` (only facts read from the PEM).

    The Certificate Authority is pre-selected only when it is proven by signature (`issuers.identify_issuer`); how it
    was identified is stored under `ISSUER_SESSION_KEY` to explain it (or list suggestions) on the form.
    """
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
    if identification is None:
        identification = issuers.identify_issuer(parsed)
    if identification.proven_authority is not None:
        initial["certificate_authority"] = str(identification.proven_authority.pk)
    if identification.method:
        initial[ISSUER_SESSION_KEY] = identification.to_session()
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


def get_missing_issuer_hint(parsed, identification):
    """Hint displayed when the issuer of an imported certificate is not in Nautobot (link to create its CA).

    The issuer is considered present when a stored CA certificate is proven to have issued the certificate, or when a
    CA is named exactly like the issuer Common Name. The issuer Common Name is the only data available about it.
    """
    if parsed.is_self_signed or not parsed.issuer_common_name or identification.method:
        return None
    url = f"{reverse('plugins:nautobot_ssl_manager:certificateauthority_add')}?{urlencode({'name': parsed.issuer_common_name})}"
    return format_html(
        'The issuer of this certificate ({}) is not in Nautobot: <a href="{}">create its Certificate Authority</a> '
        "first, or import the full chain (PEM bundle) to create it from its certificate.",
        parsed.issuer_common_name,
        url,
    )


def get_ca_certificate_hint(parsed, identification):
    """Hint displayed when importing a CA certificate. The CA is only suggested, never linked automatically.

    The issuer of the CA certificate tells the *Issued by* of the CA it belongs to: none for a self-signed certificate
    (Root CA), the CA proven by signature otherwise.
    """
    hint = "This is a CA certificate: once saved, link it to its Certificate Authority (CA certificate field)."
    if parsed.common_name:
        authorities = list(
            models.CertificateAuthority.objects.filter(name__iexact=parsed.common_name, certificate__isnull=True)[:2]
        )
        if len(authorities) == 1:
            hint += f" Suggested Certificate Authority (same name as the Common Name): {authorities[0]}."
    if parsed.is_self_signed:
        hint += " It is self-signed: its Certificate Authority is a Root CA (no Issued by)."
    elif identification.proven_authority is not None:
        hint += (
            f" Its issuer, proven by signature, is {identification.proven_authority}: "
            "set it as Issued by of its Certificate Authority."
        )
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
                    "tenant",
                    "description",
                ],
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
        extra_buttons=[
            DropdownButton(
                label="Download",
                icon="mdi-download",
                weight=100,
                required_permissions=["nautobot_ssl_manager.view_certificate"],
                children=_download_buttons(),
            ),
        ],
    )

    @action(
        detail=True,
        methods=["GET"],
        url_path="download",
        url_name="download",
        custom_view_base_action="view",
    )
    def download(self, request, *args, **kwargs):
        """Download the public certificate, optionally with its chain (see `downloads`)."""
        certificate = self.get_object()
        try:
            download = downloads.build_download(
                certificate,
                file_format=request.GET.get("file_format"),
                chain=downloads.parse_bool(request.GET.get("chain")),
                include_root=downloads.parse_bool(request.GET.get("include_root")),
                user=request.user,
            )
        except downloads.CertificateDownloadError as exc:
            messages.error(request, f"Download failed: {exc}")
            return redirect(certificate.get_absolute_url())
        return downloads.download_response(download)

    def create(self, request, *args, **kwargs):
        """Pre-fill the creation form from a previously parsed PEM (see `import_pem`)."""
        token = request.GET.get("pem_import")
        if request.method == "GET" and token:
            initial = request.session.get(PEM_IMPORT_SESSION_KEY, {}).get(token)
            if initial:
                initial = dict(initial)
                issuer = initial.pop(ISSUER_SESSION_KEY, None)
                suggestions = get_replaces_suggestions(
                    initial.get("common_name"),
                    initial.get("subject_alternative_names"),
                    exclude_fingerprint=initial.get("fingerprint_sha256"),
                )
                form = self.get_form_class()(
                    instance=self.get_object(),
                    initial=initial,
                    replaces_suggestions=suggestions,
                    issuer_hint=self._issuer_hint(issuer, request.user),
                )
                restrict_form_fields(form, request.user)
                return Response({"form": form})
            messages.warning(request, "The PEM import has expired, please import the certificate again.")
        return super().create(request, *args, **kwargs)

    @staticmethod
    def _issuer_hint(issuer, user):
        """`(method, authorities visible to the user)` from the issuer identification stored with the PEM import."""
        if not issuer or not issuer.get("method"):
            return None
        visible = models.CertificateAuthority.objects.restrict(user, "view").filter(pk__in=issuer["authorities"])
        authorities = sorted(visible, key=lambda authority: issuer["authorities"].index(str(authority.pk)))
        return (issuer["method"], authorities) if authorities else None

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
        if request.method == "POST" and form.is_valid() and form.bundle:
            plan = bundles.BundlePlan(form.bundle, user=request.user)
            review_form = forms.CertificateImportBundleForm(initial={"pem": form.cleaned_data["pem"]}, plan=plan)
            return self._render_bundle_review(request, review_form)
        if request.method == "POST" and form.is_valid():
            parsed = form.parsed
            for warning in parsed.warnings:
                messages.warning(request, warning)
            identification = issuers.identify_issuer(parsed)
            if parsed.is_ca:
                messages.info(request, get_ca_certificate_hint(parsed, identification))
            if hint := get_missing_issuer_hint(parsed, identification):
                messages.info(request, hint)
            pending = request.session.get(PEM_IMPORT_SESSION_KEY, {})
            # Keep only the most recent imports to bound the session size.
            pending = dict(list(pending.items())[-(PEM_IMPORT_SESSION_MAX_ENTRIES - 1) :])
            token = uuid4().hex
            pending[token] = build_initial_from_pem(parsed, identification)
            request.session[PEM_IMPORT_SESSION_KEY] = pending
            return redirect(f"{reverse('plugins:nautobot_ssl_manager:certificate_add')}?pem_import={token}")
        return Response({"form": form})

    @staticmethod
    def _render_bundle_review(request, form):
        """Render the review page of a PEM bundle."""
        return render(
            request,
            "nautobot_ssl_manager/certificate_import_bundle.html",
            {
                "form": form,
                "plan": form.plan,
                "entries": [
                    (entry, form.selected_field(entry), form.entry_fields(entry)) for entry in form.plan.entries
                ],
                "return_url": reverse("plugins:nautobot_ssl_manager:certificate_list"),
            },
        )

    @action(
        detail=False,
        methods=["POST"],
        url_path="import-bundle",
        url_name="import_bundle",
        custom_view_base_action="add",
    )
    def import_bundle(self, request, *args, **kwargs):
        """Confirm the review of a PEM bundle: create the selected CAs and certificates in a single transaction."""
        try:
            plan = bundles.BundlePlan.from_pem(request.POST.get("pem", ""), user=request.user)
        except utils.CertificateParseError as exc:
            messages.error(request, f"Invalid PEM bundle: {exc}")
            return redirect(reverse("plugins:nautobot_ssl_manager:certificate_import_pem"))
        form = forms.CertificateImportBundleForm(request.POST, plan=plan)
        if form.is_valid():
            try:
                changed = bundles.apply_plan(plan, form.selections, user=request.user)
            except bundles.BundleImportError as exc:
                form.add_error(None, f"Nothing was saved. {exc}")
            else:
                links = format_html_join(
                    ", ", '<a href="{}">{}</a>', ((obj.get_absolute_url(), obj) for obj in changed)
                )
                messages.success(request, format_html("Bundle imported. Created or updated: {}", links))
                certificates = [obj for obj in changed if isinstance(obj, models.Certificate)]
                target = certificates[-1] if certificates else changed[-1]
                return redirect(target.get_absolute_url())
        return self._render_bundle_review(request, form)
