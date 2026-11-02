# Certificate Provider

A Certificate Provider is the vendor or service through which certificates are obtained (for example Sectigo, Let's Encrypt or an internal PKI team). A provider can be linked to several [Certificate Authorities](certificateauthority.md).

## Fields

- `name` (string, required, unique): Name of the provider.
- `description` (string, optional): Short description.
- `portal_url` (URL, optional): Link to the provider portal or console.
- `tenant` (Tenant, optional): Tenant owning the provider account.
- `comments` (text, optional): Free-form comments (Markdown supported).

Tags, notes, contacts/teams, custom fields and relationships are supported through the standard Nautobot features.

A provider cannot be deleted while Certificate Authorities still reference it.
