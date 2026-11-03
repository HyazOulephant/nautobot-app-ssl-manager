"""Tables for nautobot_ssl_manager."""

import django_tables2 as tables
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

from nautobot_ssl_manager import models

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
