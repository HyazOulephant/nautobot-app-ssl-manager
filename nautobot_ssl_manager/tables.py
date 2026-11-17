"""Tables for nautobot_ssl_manager."""

import django_tables2 as tables
from django.utils.html import format_html
from nautobot.apps.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    LinkedCountColumn,
    StatusTableMixin,
    TagColumn,
    ToggleColumn,
)
from nautobot.tenancy.tables import TenantColumn

from nautobot_ssl_manager import choices, dns_models, models

# Same rendering as Nautobot core tree tables (Tenant Groups, Locations...): one dot per tree level,
# hidden as soon as the table is sorted on a column.
TREE_LINK = """
{% load helpers %}
{% if not table.hide_hierarchy_ui %}
{% tree_hierarchy_ui_representation record.tree_depth|as_range table.hide_hierarchy_ui %}
{% endif %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


class CertificateProviderTable(BaseTable):
    # pylint: disable=R0903
    """Table for CertificateProvider list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    portal_url = tables.URLColumn(verbose_name="Portal URL")
    tenant = TenantColumn()
    certificate_authority_count = LinkedCountColumn(
        viewname="plugins:nautobot_ssl_manager:certificateauthority_list",
        url_params={"provider": "pk"},
        verbose_name="Certificate Authorities",
    )
    tags = TagColumn(url_name="plugins:nautobot_ssl_manager:certificateprovider_list")
    actions = ButtonsColumn(models.CertificateProvider)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.CertificateProvider
        fields = (
            "pk",
            "name",
            "description",
            "portal_url",
            "tenant",
            "certificate_authority_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "tenant",
            "certificate_authority_count",
            "actions",
        )


class CertificateAuthorityTable(StatusTableMixin, BaseTable):
    # pylint: disable=R0903
    """Table for CertificateAuthority list view, displayed as a tree (Root CAs and the CAs they issued)."""

    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, attrs={"td": {"class": "text-nowrap"}})
    parent = tables.Column(linkify=True, verbose_name="Issued by")
    chain_role = tables.TemplateColumn(
        template_code="{{ record.chain_role }}",
        verbose_name="Role",
        orderable=False,
    )
    type = tables.Column()
    provider = tables.Column(linkify=True)
    portal_url = tables.URLColumn(verbose_name="Portal URL")
    tenant = TenantColumn()
    certificate_count = LinkedCountColumn(
        viewname="plugins:nautobot_ssl_manager:certificate_list",
        url_params={"certificate_authority": "pk"},
        verbose_name="Certificates",
    )
    certificate = tables.Column(linkify=True, verbose_name="CA certificate")
    certificate_expires = tables.DateTimeColumn(
        accessor="certificate__not_after",
        verbose_name="CA certificate expires",
    )
    tags = TagColumn(url_name="plugins:nautobot_ssl_manager:certificateauthority_list")
    actions = ButtonsColumn(models.CertificateAuthority)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = (
            "pk",
            "name",
            "chain_role",
            "parent",
            "type",
            "status",
            "provider",
            "tenant",
            "certificate_count",
            "certificate",
            "certificate_expires",
            "description",
            "portal_url",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "chain_role",
            "type",
            "status",
            "provider",
            "tenant",
            "certificate_count",
            "actions",
        )


class CertificateTable(StatusTableMixin, BaseTable):
    # pylint: disable=R0903
    """Table for Certificate list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    certificate_authority = tables.Column(linkify=True, verbose_name="Certificate Authority")
    subject_alternative_names = tables.Column(verbose_name="SANs", orderable=False)
    days_remaining = tables.Column(verbose_name="Days remaining", order_by=("not_after",))
    auto_renew = BooleanColumn(verbose_name="Auto-renew")
    replaces = tables.Column(linkify=True)
    validation_level = tables.Column()
    dcv_method = tables.Column(verbose_name="DCV method")
    domain_validation_record_count = LinkedCountColumn(
        viewname="plugins:nautobot_ssl_manager:domainvalidationrecord_list",
        url_params={"certificates": "pk"},
        verbose_name="Domain Validation Records",
    )
    key_algorithm = tables.Column()
    tenant = TenantColumn()
    tags = TagColumn(url_name="plugins:nautobot_ssl_manager:certificate_list")
    actions = ButtonsColumn(models.Certificate)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.Certificate
        fields = (
            "pk",
            "name",
            "status",
            "common_name",
            "certificate_authority",
            "not_after",
            "days_remaining",
            "not_before",
            "subject_alternative_names",
            "auto_renew",
            "replaces",
            "order_number",
            "key_algorithm",
            "key_size",
            "validation_level",
            "dcv_method",
            "domain_validation_record_count",
            "serial_number",
            "fingerprint_sha256",
            "tenant",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "common_name",
            "status",
            "certificate_authority",
            "not_after",
            "days_remaining",
            "auto_renew",
            "tenant",
            "actions",
        )

    def render_subject_alternative_names(self, value):
        """Render the SAN count rather than the full list."""
        return len(value) if value else "—"


DNS_MODELS_MATCH_BADGES = {
    choices.DNSModelsMatchChoices.PRESENT: "bg-success",
    choices.DNSModelsMatchChoices.DIFFERENT: "bg-warning",
    choices.DNSModelsMatchChoices.ABSENT: "bg-danger",
}


def dns_models_match_badge(value):
    """Badge of a comparison state with Nautobot DNS Models."""
    if not value:
        return format_html("{}", "—")
    label = choices.DNSModelsMatchChoices.as_dict().get(value, value)
    return format_html('<span class="badge {}">{}</span>', DNS_MODELS_MATCH_BADGES.get(value, "bg-secondary"), label)


class DomainValidationRecordTable(BaseTable):
    # pylint: disable=R0903
    """Table for DomainValidationRecord list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True, empty_values=())
    fqdn = tables.Column(verbose_name="FQDN", order_by=("zone_name", "name"))
    record_type = tables.Column(verbose_name="Type")
    zone_name = tables.Column(verbose_name="Zone")
    value = tables.Column(verbose_name="Value", order_by=("alias", "text"))
    ttl = tables.Column(verbose_name="TTL")
    certificates = tables.ManyToManyColumn(linkify_item=True, verbose_name="Certificates")
    certificate_count = LinkedCountColumn(
        viewname="plugins:nautobot_ssl_manager:certificate_list",
        url_params={"domain_validation_records": "pk"},
        verbose_name="Certificate count",
    )
    # Annotated by the list view; computed per row otherwise (e.g. table of the records of a certificate).
    dns_models_match = tables.Column(
        accessor=dns_models.ANNOTATION, verbose_name="Nautobot DNS Models", empty_values=()
    )
    tenant = TenantColumn()
    tags = TagColumn(url_name="plugins:nautobot_ssl_manager:domainvalidationrecord_list")
    actions = ButtonsColumn(models.DomainValidationRecord)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.DomainValidationRecord
        fields = (
            "pk",
            "name",
            "zone_name",
            "fqdn",
            "record_type",
            "value",
            "ttl",
            "certificates",
            "certificate_count",
            "dns_models_match",
            "tenant",
            "description",
            "comment",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "zone_name",
            "record_type",
            "value",
            "certificates",
            "dns_models_match",
            "tenant",
            "actions",
        )

    def __init__(self, *args, **kwargs):
        """Without Nautobot DNS Models, the comparison column is hidden (`base_columns` must not be modified)."""
        super().__init__(*args, **kwargs)
        if not dns_models.is_installed():
            self.columns.hide("dns_models_match")

    def render_name(self, record, value):
        """Name relative to the zone, `@` for the zone apex (as in zone files)."""
        return format_html('<a href="{}">{}</a>', record.get_absolute_url(), value or "@")

    def render_value(self, value):
        """Value of the record in monospace."""
        return format_html("<code>{}</code>", value) if value else "—"

    def render_dns_models_match(self, record, value):
        """State as a colored badge (only the DNS Models records visible to the user are considered)."""
        user = getattr(getattr(self, "request", None), "user", None)
        if value is None and user is not None and dns_models.is_installed():
            comparison = dns_models.compare(record, user=user)
            value = comparison.state if comparison else None
        return dns_models_match_badge(value)
