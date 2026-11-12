# External Interactions

This document describes external dependencies and prerequisites for this App to operate, including system requirements, API endpoints, interconnection or integrations to other applications or services, and similar topics.

## External System Integrations

### From the App to Other Systems

The app does not connect to any external system: it does not contact Certificate Authorities, providers or the endpoints using the certificates. PEM certificates are parsed locally with the [`cryptography`](https://cryptography.io/) library.

### From Other Systems to the App

External tools can read and write the inventory through the Nautobot REST API and GraphQL, with the standard Nautobot authentication and permissions.

## Nautobot REST API endpoints

| Model | Endpoint |
| ----- | -------- |
| Certificate | `/api/plugins/nautobot-ssl-manager/certificates/` |
| Certificate Authority | `/api/plugins/nautobot-ssl-manager/certificate-authorities/` |
| Certificate Provider | `/api/plugins/nautobot-ssl-manager/certificate-providers/` |

The filters described in the [data models](../models/certificate.md) pages are available as query parameters. Read-only computed fields are included in the responses:

- Certificate: `days_remaining`, `is_expired`, `is_wildcard`;
- Certificate Authority: `chain_role`.

Example: list the certificates expiring within 30 days.

```shell
curl -s \
  -H "Authorization: Token $NAUTOBOT_TOKEN" \
  -H "Accept: application/json" \
  "https://nautobot.example.com/api/plugins/nautobot-ssl-manager/certificates/?expires_within_days=30"
```

The same request with Python:

```python
import requests

response = requests.get(
    "https://nautobot.example.com/api/plugins/nautobot-ssl-manager/certificates/",
    headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    params={"expires_within_days": 30},
    timeout=30,
)
response.raise_for_status()
for certificate in response.json()["results"]:
    print(certificate["common_name"], certificate["not_after"], certificate["days_remaining"])
```

### Download a certificate

`GET /api/plugins/nautobot-ssl-manager/certificates/<id>/download/` returns the public certificate as a file (see [Download](../models/certificate.md#download)). Query parameters:

- `file_format`: `pem` (default), `der` (single certificate only) or `p7b` (PKCS#7, DER encoded);
- `chain`: `true` to append the CA certificates of the chain;
- `include_root`: with `chain`, `true` to also include the self-signed Root CA certificate.

The response is `400` with a `detail` message when the file cannot be built (no PEM, incomplete or inconsistent chain), and `403` when a Certificate Authority or CA certificate of the chain is not visible to the user.

Example: download the certificate with its intermediate CAs (without the Root CA), as usually served by a web server.

```shell
curl -s -f \
  -H "Authorization: Token $NAUTOBOT_TOKEN" \
  -o fullchain.pem \
  "https://nautobot.example.com/api/plugins/nautobot-ssl-manager/certificates/$CERTIFICATE_ID/download/?chain=true"
```

!!! note
    The import from PEM is a UI feature. Through the REST API, the certificate data must be sent explicitly; a `pem` value is still validated (a private key is rejected).
