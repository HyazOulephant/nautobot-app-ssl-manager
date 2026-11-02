"""Associate default statuses with the CertificateAuthority model."""

from django.db import migrations

# (name, hex color, description) - used only if the Status does not already exist.
CERTIFICATE_AUTHORITY_STATUSES = (
    ("Active", "4caf50", "Certificate Authority is in use"),
    ("Deprecated", "f44336", "Certificate Authority is no longer used for new certificates"),
    ("Retired", "f44336", "Certificate Authority is no longer in use"),
)


def populate_statuses(apps, schema_editor):
    """Create (if needed) and associate default statuses with CertificateAuthority."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")
    CertificateAuthority = apps.get_model("nautobot_ssl_manager", "CertificateAuthority")

    content_type = ContentType.objects.get_for_model(CertificateAuthority)
    for name, color, description in CERTIFICATE_AUTHORITY_STATUSES:
        status, _ = Status.objects.get_or_create(name=name, defaults={"color": color, "description": description})
        status.content_types.add(content_type)


def remove_statuses(apps, schema_editor):
    """Remove the CertificateAuthority association from the default statuses (statuses themselves are kept)."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")
    CertificateAuthority = apps.get_model("nautobot_ssl_manager", "CertificateAuthority")

    content_type = ContentType.objects.get_for_model(CertificateAuthority)
    for status in Status.objects.filter(name__in=[name for name, _, _ in CERTIFICATE_AUTHORITY_STATUSES]):
        status.content_types.remove(content_type)


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("nautobot_ssl_manager", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_statuses, remove_statuses),
    ]
