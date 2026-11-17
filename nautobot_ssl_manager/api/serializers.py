"""API serializers for nautobot_ssl_manager."""

from drf_spectacular.utils import extend_schema_field
from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin, TreeModelSerializerMixin
from rest_framework import serializers

from nautobot_ssl_manager import choices, dns_models, models


class CertificateProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """CertificateProvider Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.CertificateProvider
        fields = "__all__"


class CertificateAuthoritySerializer(  # pylint: disable=too-many-ancestors
    NautobotModelSerializer, TaggedModelSerializerMixin, TreeModelSerializerMixin
):
    """CertificateAuthority Serializer."""

    chain_role = serializers.CharField(read_only=True)

    class Meta:
        """Meta attributes."""

        model = models.CertificateAuthority
        fields = "__all__"


class CertificateSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """Certificate Serializer."""

    days_remaining = serializers.IntegerField(read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True, allow_null=True)
    is_wildcard = serializers.BooleanField(read_only=True)

    class Meta:
        """Meta attributes."""

        model = models.Certificate
        fields = "__all__"


class DomainValidationRecordSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """DomainValidationRecord Serializer."""

    fqdn = serializers.CharField(read_only=True)
    dns_models_match = serializers.SerializerMethodField(
        help_text="Comparison with Nautobot DNS Models: present, different, absent (null when it is not installed)"
    )

    class Meta:
        """Meta attributes."""

        model = models.DomainValidationRecord
        fields = "__all__"
        # The unique constraint involves optional fields (text, alias): DRF would make them required. It is validated
        # by the model instead (`full_clean()`).
        validators = []

    @extend_schema_field(
        serializers.ChoiceField(choices=choices.DNSModelsMatchChoices.CHOICES, allow_null=True, read_only=True)
    )
    def get_dns_models_match(self, obj):
        """State annotated by the viewset (see `dns_models.annotate`)."""
        return dns_models.get_match(obj)
