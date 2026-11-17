# Domain Validation Record

A Domain Validation Record is a DNS record used for the Domain Control Validation (DCV) of certificates: for example the `_acme-challenge` CNAME delegating ACME `dns-01` challenges to another zone, or a TXT record holding the token of a Certificate Authority. A record can be linked to several certificates (a delegation is reused at each renewal), and a certificate to several records.

The DCV method itself is stored on the [Certificate](certificate.md#domain-validation) (`dcv_method`).

## Fields

The fields follow the conventions of [Nautobot DNS Models](https://github.com/nautobot/nautobot-app-dns-models) (`TXTRecord`, `CNAMERecord`), so that a record can be copied from one app to the other field by field:

| Field | Nautobot DNS Models | Description |
| ----- | ------------------- | ----------- |
| `record_type` | `TXTRecord` or `CNAMERecord` | `TXT` or `CNAME` (required). |
| `name` | `name` | Name relative to the zone (e.g. `_acme-challenge`), empty for the zone apex. A name ending with the zone and a dot (e.g. `_acme-challenge.example.com.`) is made relative. Up to 200 characters. |
| `zone_name` | `zone.name` | FQDN of the DNS zone (e.g. `example.com`, required). Stored as a name: the app does not depend on Nautobot DNS Models. |
| `text` | `text` | TXT records only, up to 256 characters. Optional: leave it empty when the value changes at each issuance (e.g. ACME `dns-01`). |
| `alias` | `alias` | CNAME records only (required for them): FQDN of the alias. |
| `ttl` | `ttl` (`_ttl`) | Optional; empty means the TTL of the zone. |
| `description`, `comment` | `description`, `comment` | Free text. |
| `certificates` | — | Certificates validated with this record. |
| `tenant` | — | Optional tenant. |

Computed (read-only): `fqdn` (`name` + `.` + `zone_name`).

As in Nautobot DNS Models, the letter case is kept and DNS names are compared ignoring the case; a trailing dot is removed. The same record (type, name, zone, text and alias) cannot be created twice.

Tags, notes, contacts/teams, custom fields, relationships and change logging are supported through the standard Nautobot features.

## Views

The records are listed in the menu **SSL Manager > Domain Validation > DNS Validation Records**, with their certificates. The detail view of a certificate shows a *Domain Validation* panel (DCV method and validation level) and the table of its Domain Validation Records.

Filters: `record_type`, `fqdn` (exact, ignoring the case), `zone_name`, `certificates`, `has_certificates`, `certificate_expires_within_days` (records linked to a certificate not yet expired and expiring within N days) and, when Nautobot DNS Models is installed, `dns_models_match`.

## Nautobot DNS Models (optional)

The app works without Nautobot DNS Models. When it is installed (see [Install](../admin/install.md#optional-nautobot-dns-models)), each Domain Validation Record is compared with the TXT / CNAME records of DNS Models **each time it is displayed**; nothing is stored, so a record deleted or modified in DNS Models is reported at once, without synchronization job:

| State | Meaning |
| ----- | ------- |
| Present | A DNS Models record with the same type, name, zone and value (text or alias) exists. A TXT record without text is present as soon as a record with the same name exists. |
| Different | DNS Models records with the same type, name and zone exist, but with another value (e.g. a modified CNAME delegation). |
| Absent | No DNS Models record with the same type, name and zone. |

- The name is compared both relative to the zone and as a fully qualified name, as both forms can be found in DNS Models. A zone name can exist in several DNS views: all the matching records are listed.
- Only the DNS Models records visible to the user (object permissions) are considered.
- The state is shown in the list (*Nautobot DNS Models* column), in the detail view (with links to the matching records) and in the REST API (`dns_models_match`, `null` when DNS Models is not installed). The `dns_models_match` filter lists, for example, the absent records linked to certificates expiring within 30 days: `?dns_models_match=absent&certificate_expires_within_days=30`.
- For an absent record, *Create in Nautobot DNS Models* opens the creation form of DNS Models pre-filled with the values of the record (the zone is selected when exactly one zone has this name). The record is created by DNS Models itself, with its own validation and permissions (`add_txtrecord` / `add_cnamerecord`).

!!! note
    Nautobot DNS Models is an inventory too: a record present in DNS Models does not prove that the DNS zone actually publishes it. The app does not query DNS servers (see [External Interactions](../user/external_interactions.md)).

CAA records (Certificate Authorities authorized for a domain) are not modelled in Nautobot DNS Models 2.3.0 / 3.0.0 and are out of scope.
