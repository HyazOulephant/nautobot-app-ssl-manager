# Certificate

A Certificate describes an SSL/TLS certificate. Only the **public** certificate is stored: private keys are rejected and must never be stored in Nautobot.

## Fields

- `name` (string, required): Display name (not unique, a domain usually has several certificates over time).
- `common_name` (string, required): Common Name (CN) of the certificate subject.
- `subject_alternative_names` (list, optional): Subject Alternative Names. DNS names (wildcards allowed) and IP addresses are stored as-is; other types are prefixed with `email:` or `uri:`. In the form, enter one entry per line.
- `certificate_authority` ([Certificate Authority](certificateauthority.md), optional): Issuing CA. The detail view shows the resulting certification chain, up to the Root CA (see [Certification chain](certificateauthority.md#certification-chain)).
- `serial_number` (string, optional): Serial number, stored as lowercase hexadecimal without separators.
- `fingerprint_sha256` (string, optional, unique): SHA-256 fingerprint, stored as lowercase hexadecimal without separators.
- `not_before` (date/time, optional): Start of validity.
- `not_after` (date/time, required): Expiration.
- `status` (Status, required): Lifecycle status. `Planned`, `Active`, `Revoked` and `Retired` are associated by default. Expiration is computed from `not_after` and is not a status.
- `replaces` (Certificate, optional): Previous certificate replaced by this one (renewal). The previous certificate shows it as *Replaced by*.
- `auto_renew` (boolean, optional): Whether the certificate is renewed automatically. Left empty (unknown) by default: it is never guessed.
- `order_number` (string, optional): Order number at the provider.
- `key_algorithm` (choice, optional): `RSA`, `ECDSA` or `Ed25519`.
- `key_size` (integer, optional): Key size in bits.
- `validation_level` (choice, optional): `DV`, `OV` or `EV`.
- `extended_key_usage` (list, optional): Extended Key Usage purposes (RFC 5280): TLS Server Authentication, TLS Client Authentication, Code Signing, Email Protection (S/MIME), Time Stamping, OCSP Signing.
- `pem` (text, optional): Public certificate in PEM format.
- `tenant` (Tenant, optional), `description` (string, optional), `comments` (text, optional).

Computed (read-only): `days_remaining`, `is_expired`, `is_wildcard`.

Tags, notes, contacts/teams, custom fields, relationships and change logging are supported through the standard Nautobot features.

## Import from PEM

*SSL Manager > Certificates > Import from PEM* reads a pasted PEM certificate and opens the creation form pre-filled with the data read from the certificate:

- Common Name, SANs, serial number, SHA-256 fingerprint, validity dates, key algorithm and size, Extended Key Usage;
- validation level, only if a CA/Browser Forum policy OID (DV `2.23.140.1.2.1`, OV `2.23.140.1.2.2`, EV `2.23.140.1.1`) is present;
- Certificate Authority, only if a CA named exactly like the issuer Common Name exists.

Nothing is guessed: status, auto-renew, order number, tenant and *replaces* are left for the user. Certificates that may be replaced (same CN or shared SANs, not yet replaced) are listed as suggestions next to the *replaces* field but are never selected automatically.

The import is refused if the PEM contains a private key, if the certificate already exists (same fingerprint), or if a bundle contains several end-entity certificates.
