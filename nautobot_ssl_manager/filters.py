"""Filtering for nautobot_ssl_manager."""

from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone
from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
)

from nautobot_ssl_manager import choices, models, utils


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
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CertificateAuthority.objects.all(),
        to_field_name="name",
        label="Issued by (name or ID)",
    )
    has_parent = RelatedMembershipBooleanFilter(
        field_name="parent",
        label="Has issuer (Intermediate CA)",
    )
    children = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CertificateAuthority.objects.all(),
        to_field_name="name",
        label="Issued CAs (name or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has issued CAs",
    )
    certificate = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.Certificate.objects.all(),
        to_field_name="name",
        label="CA certificate (name or ID)",
    )
    has_certificate = RelatedMembershipBooleanFilter(
        field_name="certificate",
        label="Has CA certificate",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.CertificateAuthority
        fields = "__all__"


class CertificateFilterSet(  # pylint: disable=too-many-ancestors
    StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet
):
    """Filter for Certificate."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "common_name": "icontains",
            "serial_number": "icontains",
            "fingerprint_sha256": "icontains",
            "order_number": "icontains",
            "description": "icontains",
            "comments": "icontains",
        },
    )
    certificate_authority = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.CertificateAuthority.objects.all(),
        to_field_name="name",
        label="Certificate Authority (name or ID)",
    )
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="certificate_authority__provider",
        queryset=models.CertificateProvider.objects.all(),
        to_field_name="name",
        label="Provider (name or ID)",
    )
    replaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.Certificate.objects.all(),
        to_field_name="name",
        label="Replaces (name or ID)",
    )
    has_replaced_by = RelatedMembershipBooleanFilter(
        field_name="replaced_by",
        label="Has been replaced",
    )
    is_ca_certificate = RelatedMembershipBooleanFilter(
        field_name="ca_certificate_of",
        label="Is the certificate of a Certificate Authority",
    )
    san = django_filters.CharFilter(method="filter_san", label="SAN (exact entry)")
    extended_key_usage = django_filters.MultipleChoiceFilter(
        choices=choices.ExtendedKeyUsageChoices,
        method="filter_extended_key_usage",
        label="Extended Key Usage",
    )
    key_algorithm = django_filters.MultipleChoiceFilter(choices=choices.KeyAlgorithmChoices)
    validation_level = django_filters.MultipleChoiceFilter(choices=choices.ValidationLevelChoices)
    expired = django_filters.BooleanFilter(method="filter_expired", label="Expired")
    expires_within_days = django_filters.NumberFilter(
        method="filter_expires_within_days", label="Expires within N days (not yet expired)"
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.Certificate
        fields = "__all__"

    def filter_san(self, queryset, name, value):  # pylint: disable=unused-argument
        """Certificates whose SAN list contains exactly this entry."""
        if not value:
            return queryset
        try:
            value = utils.normalize_san(value)
        except ValueError:
            return queryset.none()
        return queryset.filter(subject_alternative_names__contains=[value])

    def filter_extended_key_usage(self, queryset, name, value):  # pylint: disable=unused-argument
        """Certificates having at least one of the given EKU values."""
        if not value:
            return queryset
        query = Q()
        for usage in value:
            query |= Q(extended_key_usage__contains=[usage])
        return queryset.filter(query)

    def filter_expired(self, queryset, name, value):  # pylint: disable=unused-argument
        """Expired (True) or not yet expired (False) certificates."""
        if value is None:
            return queryset
        now = timezone.now()
        return queryset.filter(not_after__lte=now) if value else queryset.filter(not_after__gt=now)

    def filter_expires_within_days(self, queryset, name, value):  # pylint: disable=unused-argument
        """Certificates not yet expired and expiring within the given number of days."""
        if value is None:
            return queryset
        now = timezone.now()
        return queryset.filter(not_after__gt=now, not_after__lte=now + timedelta(days=int(value)))
