# Frequently Asked Questions

## Can I store private keys in the app?

No. Only public certificates are stored. A PEM containing a private key is rejected, from the UI as well as from the REST API.

## Why is "Expired" not a status?

Expiration is computed from the `not_after` date (`is_expired`, `days_remaining`) and can be filtered on (`expired`, `expires_within_days`). Statuses describe the lifecycle decided by the users (`Planned`, `Active`, `Revoked`, `Retired`), which is independent from the date.

## Why was the Certificate Authority not filled during the import from PEM?

When a single certificate is imported, the CA is pre-selected only if it is proven by signature: the CA certificate of the issuing CA must be linked to it, with its PEM. A CA named like the issuer Common Name is only suggested, as the name alone does not prove anything. If several CAs are proven (cross-signing), they are listed and you choose. See [Issuing CA identification](../models/certificate.md#issuing-ca-identification).

When a PEM bundle (full chain) is imported, the issuer is established by signature verification instead; it is left empty when several issuers are possible or none is found (see [Import a PEM bundle](../models/certificate.md#import-a-pem-bundle-full-chain)).

## Why was the validation level not filled during the import from PEM?

The validation level is filled only if the certificate contains one of the CA/Browser Forum policy OIDs (DV, OV or EV). Otherwise it is left empty rather than guessed.

## Why can't I delete a Certificate Authority or a Provider?

A Certificate Authority cannot be deleted while it still has issued CAs, and a Provider cannot be deleted while Certificate Authorities still reference it. Reassign or delete the dependent objects first.

## Is the app connected to my CA or certificate vendor?

No. The app is an inventory: it does not issue, renew or retrieve certificates. See [External Interactions](external_interactions.md).
