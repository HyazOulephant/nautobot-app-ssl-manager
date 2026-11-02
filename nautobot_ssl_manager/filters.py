"""Filtering for nautobot_ssl_manager."""

import django_filters
from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
)

from nautobot_ssl_manager import choices, models


class CertificateProviderFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for CertificateProvider."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "portal_url": "icontains",
            "comments": "icontains",
        },
    )
    has_certificate_authorities = RelatedMembershipBooleanFilter(
        field_name="certificate_authorities",
        label="Has certificate authorities",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.CertificateProvider
        fields = "__all__"


class CertificateAuthorityFilterSet(  # pylint: disable=too-many-ancestors
    StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet
):
    """Filter for CertificateAuthority."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "portal_url": "icontains",
            "comments": "icontains",
        },
    )
    type = django_filters.MultipleChoiceFilter(choices=choices.CertificateAuthorityTypeChoices)
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CertificateProvider.objects.all(),
        to_field_name="name",
        label="Provider (name or ID)",
    )
    has_provider = RelatedMembershipBooleanFilter(
        field_name="provider",
        label="Has provider",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.CertificateAuthority
        fields = "__all__"
