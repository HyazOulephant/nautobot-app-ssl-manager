"""Associate default statuses with the Certificate model."""

from django.db import migrations

# (name, hex color, description) - color/description are used only if the Status does not already exist.
CERTIFICATE_STATUSES = (
    ("Planned", "00bcd4", "Certificate has been requested or is being issued"),
    ("Active", "4caf50", "Certificate is in use"),
    ("Revoked", "aa1409", "Certificate has been revoked"),
    ("Retired", "f44336", "Certificate is no longer in use"),
)


def populate_statuses(apps, schema_editor):
    """Create (if needed) and associate default statuses with Certificate."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")
    Certificate = apps.get_model("nautobot_ssl_manager", "Certificate")

    content_type = ContentType.objects.get_for_model(Certificate)
    for name, color, description in CERTIFICATE_STATUSES:
        status, _ = Status.objects.get_or_create(name=name, defaults={"color": color, "description": description})
        status.content_types.add(content_type)


def remove_statuses(apps, schema_editor):
    """Remove the Certificate association from the default statuses (statuses themselves are kept)."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")
    Certificate = apps.get_model("nautobot_ssl_manager", "Certificate")

    content_type = ContentType.objects.get_for_model(Certificate)
    for status in Status.objects.filter(name__in=[name for name, _, _ in CERTIFICATE_STATUSES]):
        status.content_types.remove(content_type)


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("nautobot_ssl_manager", "0003_certificate"),
    ]

    operations = [
        migrations.RunPython(populate_statuses, remove_statuses),
    ]
