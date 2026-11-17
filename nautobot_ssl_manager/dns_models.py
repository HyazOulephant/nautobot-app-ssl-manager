"""Optional integration with Nautobot DNS Models (`nautobot_dns_models`).

The app never depends on Nautobot DNS Models: nothing is stored about its records. When it is installed, each
Domain Validation Record is compared, at display time, with the TXT / CNAME records of DNS Models:

- present: a record with the same type, name, zone and value (text or alias) exists;
- different: records with the same type, name and zone exist, but with another value;
- absent: no record with the same type, name and zone exists.

A TXT record without text (value changing at each issuance, e.g. ACME dns-01) is present as soon as a record with the
same name exists. In DNS Models, a record name is relative to its zone, but a fully qualified name is also accepted.
"""

from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.apps import apps
from django.db.models import Case, CharField, Exists, OuterRef, Q, Value, When
from django.db.models.functions import Concat
from django.urls import NoReverseMatch, reverse

from nautobot_ssl_manager.choices import DNSModelsMatchChoices, DNSRecordTypeChoices

APP_LABEL = "nautobot_dns_models"
MODEL_NAMES = {
    DNSRecordTypeChoices.TXT: "TXTRecord",
    DNSRecordTypeChoices.CNAME: "CNAMERecord",
}
ANNOTATION = "dns_models_match"


def is_installed():
    """True when Nautobot DNS Models is installed (in `PLUGINS`)."""
    return apps.is_installed(APP_LABEL)


def get_record_model(record_type):
    """DNS Models model for a record type (None when DNS Models is not installed)."""
    if not is_installed() or record_type not in MODEL_NAMES:
        return None
    return apps.get_model(APP_LABEL, MODEL_NAMES[record_type])


def _restricted(model, user):
    queryset = model.objects.all()
    return queryset.restrict(user, "view") if user is not None else queryset


def _normalize_alias(value):
    return str(value or "").strip().lower().rstrip(".")


@dataclass
class Comparison:
    """Result of the comparison of a Domain Validation Record with DNS Models."""

    state: str
    # DNS Models records with the same type, name and zone, and whether their value matches.
    matches: list = field(default_factory=list)

    @property
    def label(self):
        """Human readable state."""
        return DNSModelsMatchChoices.as_dict().get(self.state, self.state)


def compare(record, user=None):
    """Compare a Domain Validation Record with DNS Models (None when DNS Models is not installed).

    Only the DNS Models records visible to `user` are considered.
    """
    model = get_record_model(record.record_type)
    if model is None:
        return None
    names = {record.name.lower(), record.fqdn.lower()}
    candidates = (
        _restricted(model, user)
        .filter(zone__name__iexact=record.zone_name)
        .filter(Q(name__iexact=record.name) | Q(name__iexact=record.fqdn))
        .select_related("zone")
    )
    matches = []
    for candidate in candidates:
        if candidate.name.lower() not in names:
            continue
        if record.record_type == DNSRecordTypeChoices.CNAME:
            same_value = _normalize_alias(candidate.alias) == _normalize_alias(record.alias)
        else:
            same_value = not record.text or candidate.text == record.text
        matches.append((candidate, same_value))
    if any(same_value for _, same_value in matches):
        state = DNSModelsMatchChoices.PRESENT
    elif matches:
        state = DNSModelsMatchChoices.DIFFERENT
    else:
        state = DNSModelsMatchChoices.ABSENT
    return Comparison(state=state, matches=matches)


def _candidates_subquery(record_type, user):
    """DNS Models records with the same name and zone as the outer Domain Validation Record."""
    fqdn = Concat(OuterRef("name"), Value("."), OuterRef("zone_name"), output_field=CharField())
    return (
        _restricted(get_record_model(record_type), user)
        .filter(zone__name__iexact=OuterRef("zone_name"))
        .filter(Q(name__iexact=OuterRef("name")) | Q(name__iexact=fqdn))
    )


def annotate(queryset, user=None):
    """Annotate Domain Validation Records with `dns_models_match` (unchanged when DNS Models is not installed).

    Same rules as `compare()`, computed by the database (used by the list view, the REST API and the filter).
    """
    if not is_installed():
        return queryset
    txt = _candidates_subquery(DNSRecordTypeChoices.TXT, user)
    cname = _candidates_subquery(DNSRecordTypeChoices.CNAME, user)
    alias_with_dot = Concat(OuterRef("alias"), Value("."), output_field=CharField())
    txt_name = Exists(txt)
    txt_value = Exists(txt.filter(text=OuterRef("text")))
    cname_name = Exists(cname)
    cname_value = Exists(cname.filter(Q(alias__iexact=OuterRef("alias")) | Q(alias__iexact=alias_with_dot)))
    present = Value(DNSModelsMatchChoices.PRESENT)
    different = Value(DNSModelsMatchChoices.DIFFERENT)
    return queryset.annotate(
        **{
            ANNOTATION: Case(
                When(txt_name, record_type=DNSRecordTypeChoices.TXT, text="", then=present),
                When(txt_value, record_type=DNSRecordTypeChoices.TXT, then=present),
                When(txt_name, record_type=DNSRecordTypeChoices.TXT, then=different),
                When(cname_value, record_type=DNSRecordTypeChoices.CNAME, then=present),
                When(cname_name, record_type=DNSRecordTypeChoices.CNAME, then=different),
                default=Value(DNSModelsMatchChoices.ABSENT),
                output_field=CharField(),
            )
        }
    )


def get_match(record):
    """`dns_models_match` annotation of a record, or None when not annotated (or DNS Models is not installed)."""
    return getattr(record, ANNOTATION, None)


def get_create_url(record, user=None):
    """URL of the DNS Models creation form pre-filled with the values of the record (None if not available).

    The zone is pre-selected only when exactly one DNS zone with this name is visible (a zone name can exist in several
    DNS views). The record is created by DNS Models itself, with its own validation and permissions.
    """
    model = get_record_model(record.record_type)
    if model is None:
        return None
    try:
        url = reverse(f"plugins:{APP_LABEL}:{model._meta.model_name}_add")
    except NoReverseMatch:
        return None
    params = {"name": record.name}
    zones = list(_restricted(apps.get_model(APP_LABEL, "DNSZone"), user).filter(name__iexact=record.zone_name)[:2])
    if len(zones) == 1:
        params["zone"] = str(zones[0].pk)
    if record.record_type == DNSRecordTypeChoices.CNAME:
        params["alias"] = record.alias
    elif record.text:
        params["text"] = record.text
    if record.ttl is not None:
        params["_ttl"] = record.ttl
    if record.description:
        params["description"] = record.description
    if record.comment:
        params["comment"] = record.comment
    params["return_url"] = record.get_absolute_url()
    return f"{url}?{urlencode(params)}"
