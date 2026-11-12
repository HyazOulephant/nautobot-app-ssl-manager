# Certificate Authority

A Certificate Authority (CA) is the entity issuing SSL/TLS certificates.

## Fields

- `name` (string, required, unique): Name of the CA.
- `parent` / *Issued by* ([Certificate Authority](certificateauthority.md), optional): CA that issued this CA's certificate. Leave empty for a Root CA.
- `certificate` / *CA certificate* ([Certificate](certificate.md), optional): Certificate of this CA (its own certificate, not a certificate it issued). See [CA certificate](#ca-certificate).
- `type` (choice, required): `public` (publicly trusted CA) or `private` (internal / non publicly trusted CA).
- `status` (Status, required): Lifecycle status. `Active`, `Deprecated` and `Retired` are associated by default; other statuses can be added from *Extensibility > Statuses*.
- `provider` ([Certificate Provider](certificateprovider.md), optional): Vendor or service through which certificates from this CA are obtained.
- `description` (string, optional): Short description.
- `portal_url` (URL, optional): Link to the CA portal or console.
- `tenant` (Tenant, optional): Tenant owning the CA.
- `comments` (text, optional): Free-form comments (Markdown supported).

## Certification chain

Certificate Authorities form a tree through *Issued by*:

- a CA without issuer is a **Root CA**;
- a CA with an issuer is an **Intermediate CA**.

This role is not stored: it is deduced from the tree and exposed as `chain_role` (read-only) in the REST API.

A CA cannot be issued by itself or by one of the CAs it issued, and a CA cannot be deleted while it still has issued CAs.

The Certificate Authorities list is displayed as a tree (as long as it is not sorted on a column). The detail view of a CA and of a [Certificate](certificate.md) shows a *Certification chain* panel, from the Root CA down to the displayed object. The CA detail view also lists the CAs and the certificates it issued.

Available filters: `parent` (name or ID), `has_parent`, `children` (name or ID), `has_children`.

## CA certificate

A CA can be linked to its own certificate, stored as a regular [Certificate](certificate.md). The CA detail view shows this certificate with its expiration date and the number of days remaining; the Certificate Authorities list has optional *CA certificate* and *CA certificate expires* columns. The certificate detail view shows the CA it belongs to (*CA certificate of*).

A certificate can be the CA certificate of one CA only. Deleting the certificate unlinks it from the CA (the CA is kept). When a CA certificate is renewed, link the new certificate to the CA and record the previous one in its `replaces` field.

The link is refused when the data stored in Nautobot proves it is inconsistent:

- the PEM of the certificate is known and does not contain `basicConstraints CA:TRUE`;
- the *Certificate Authority* (issuer) of the certificate is set and is not the CA *Issued by* (or the CA itself for a self-signed Root CA);
- the PEMs of the certificate and of the issuing CA certificate are both known, and the certificate issuer does not match the subject of the issuing CA certificate.

These checks also apply when a certificate already linked to a CA is edited. When the data is missing (no PEM, no issuer), nothing is checked.

The CA certificate is never linked automatically. The CA edit form lists, as suggestions, the certificates not yet linked to a CA whose Common Name is the CA name. When a CA certificate is imported from a PEM, a message reminds to link it to its CA and names the CA with the same name as the Common Name, if there is exactly one.

To follow the expiration of CA certificates, filter the Certificates with `is_ca_certificate=True` combined with `expired` or `expires_within_days`.

Available filters: `certificate` (name or ID), `has_certificate`.

Tags, notes, contacts/teams, custom fields and relationships are supported through the standard Nautobot features.
