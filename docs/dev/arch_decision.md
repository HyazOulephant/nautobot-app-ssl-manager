# Architecture Decision Records

The intention is to document deviations from a standard Model View Controller (MVC) design.

## Only public certificates are stored

Private keys are rejected at model validation (UI and REST API). Nautobot is not a secrets store, and storing private keys would make the whole database sensitive.

## Nothing is guessed

Fields that cannot be read reliably from the certificate are left empty rather than inferred: `auto_renew` is a nullable boolean (unknown by default), the validation level is filled from the PEM only when a CA/Browser Forum policy OID is present, the CA only when a CA named exactly like the issuer Common Name exists, and the replaced certificate is only suggested, never selected.

## Expiration is computed, not a status

Expiration depends on the date and would require a periodic job to stay accurate as a status. It is computed from `not_after` (`is_expired`, `days_remaining`) and exposed as filters, while statuses describe the lifecycle decided by users.

## Root / Intermediate role is deduced from the CA tree

Certificate Authorities use Nautobot's tree model (`parent`). The `chain_role` is deduced from the presence of a parent instead of being stored, so it cannot become inconsistent with the tree.
