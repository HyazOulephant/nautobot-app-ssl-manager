# Certificate Authority

A Certificate Authority (CA) is the entity issuing SSL/TLS certificates.

## Fields

- `name` (string, required, unique): Name of the CA.
- `type` (choice, required): `public` (publicly trusted CA) or `private` (internal / non publicly trusted CA).
- `status` (Status, required): Lifecycle status. `Active`, `Deprecated` and `Retired` are associated by default; other statuses can be added from *Extensibility > Statuses*.
- `provider` ([Certificate Provider](certificateprovider.md), optional): Vendor or service through which certificates from this CA are obtained.
- `description` (string, optional): Short description.
- `portal_url` (URL, optional): Link to the CA portal or console.
- `tenant` (Tenant, optional): Tenant owning the CA.
- `comments` (text, optional): Free-form comments (Markdown supported).

Tags, notes, contacts/teams, custom fields and relationships are supported through the standard Nautobot features.
