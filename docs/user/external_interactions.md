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

!!! note
    The import from PEM is a UI feature. Through the REST API, the certificate data must be sent explicitly; a `pem` value is still validated (a private key is rejected).
