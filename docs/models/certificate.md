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

A certificate can be the certificate of a Certificate Authority (see [CA certificate](certificateauthority.md#ca-certificate)); its detail view then shows *CA certificate of*. The `is_ca_certificate` filter lists (or excludes) these certificates.

Tags, notes, contacts/teams, custom fields, relationships and change logging are supported through the standard Nautobot features.

## Import from PEM

*SSL Manager > Certificates > Import from PEM* reads a pasted PEM certificate and opens the creation form pre-filled with the data read from the certificate:

- Common Name, SANs, serial number, SHA-256 fingerprint, validity dates, key algorithm and size, Extended Key Usage;
- validation level, only if a CA/Browser Forum policy OID (DV `2.23.140.1.2.1`, OV `2.23.140.1.2.2`, EV `2.23.140.1.1`) is present;
- Certificate Authority, only if a CA named exactly like the issuer Common Name exists.

Nothing is guessed: status, auto-renew, order number, tenant and *replaces* are left for the user. Certificates that may be replaced (same CN or shared SANs, not yet replaced) are listed as suggestions next to the *replaces* field but are never selected automatically.

The import is refused if the PEM contains a private key, if the certificate already exists (same fingerprint), or if a bundle contains several end-entity certificates.

## Download

The *Download* menu of the certificate detail view serves the public certificate stored in the `pem` field, optionally with its chain. Private keys are never stored, so they are never part of a download.

| Entry | Format | File name (example) |
| ----- | ------ | ------------------- |
| Certificate (PEM) | PEM | `www.example.com.pem` |
| Certificate (DER) | DER (binary, single certificate) | `www.example.com.der` |
| Certificate + chain (PEM) | PEM bundle: the certificate, then its intermediate CA certificates | `www.example.com-chain.pem` |
| Certificate + chain + root (PEM) | PEM bundle: the certificate, its intermediate CA certificates, then the Root CA certificate | `www.example.com-chain-with-root.pem` |
| Certificate + chain + root (PKCS#7) | PKCS#7 `.p7b`, DER encoded, certificates only | `www.example.com-chain-with-root.p7b` |

The file name is built from the Common Name (or the name): `*` is replaced with `wildcard` and any character other than letters, digits, `.`, `_` and `-` is replaced with `_`. In a PEM bundle, the certificates are ordered from the certificate up to the Root CA; a PKCS#7 file stores its certificates as a set, without significant order.

The chain is built from the Certificate Authority tree (issuing CA, then its issuers), using the [CA certificate](certificateauthority.md#ca-certificate) linked to each CA. A self-signed CA certificate (Root CA) is only included in the *with root* entries; when the top CA of the tree is not self-signed (the Root CA is not recorded in Nautobot), its certificate is always included.

The download fails with an explicit message, instead of returning an incomplete or wrong file, when:

- no PEM is stored for the certificate;
- no Certificate Authority is set on the certificate (chain only);
- a CA of the chain has no CA certificate linked, or its CA certificate has no PEM (the CAs concerned are listed);
- the chain is inconsistent: a certificate issuer does not match the subject of the next CA certificate.

Unavailable entries are disabled in the menu, with the reason displayed on hover. Downloading requires the permission to view the certificate; the chain entries also require the permission to view the Certificate Authorities and CA certificates of the chain.
