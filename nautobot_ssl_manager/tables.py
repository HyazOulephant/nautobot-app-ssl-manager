"""Tables for nautobot_ssl_manager."""

import django_tables2 as tables
from nautobot.apps.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    StatusTableMixin,
    TagColumn,
    ToggleColumn,
)
from nautobot.tenancy.tables import TenantColumn

from nautobot_ssl_manager import models


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
    """Table for CertificateAuthority list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    type = tables.Column()
    provider = tables.Column(linkify=True)
    portal_url = tables.URLColumn(verbose_name="Portal URL")
    tenant = TenantColumn()
    tags = TagColumn(url_name="plugins:nautobot_ssl_manager:certificateauthority_list")
    actions = ButtonsColumn(models.CertificateAuthority)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = (
            "pk",
            "name",
            "type",
            "status",
            "provider",
            "tenant",
            "description",
            "portal_url",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "type",
            "status",
            "provider",
            "tenant",
            "actions",
        )
