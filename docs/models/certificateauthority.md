# Certificate Authority

A Certificate Authority (CA) is the entity issuing SSL/TLS certificates.

## Fields

- `name` (string, required, unique): Name of the CA.
- `parent` / *Issued by* ([Certificate Authority](certificateauthority.md), optional): CA that issued this CA's certificate. Leave empty for a Root CA.
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

Tags, notes, contacts/teams, custom fields and relationships are supported through the standard Nautobot features.
