"""Choice sets for Nautobot SSL Manager."""

from nautobot.apps.choices import ChoiceSet


class CertificateAuthorityTypeChoices(ChoiceSet):
    """Trust scope of a Certificate Authority."""

    TYPE_PUBLIC = "public"
    TYPE_PRIVATE = "private"

    CHOICES = (
        (TYPE_PUBLIC, "Public"),
        (TYPE_PRIVATE, "Private"),
    )
