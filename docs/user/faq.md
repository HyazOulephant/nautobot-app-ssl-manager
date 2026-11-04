# Frequently Asked Questions

## Can I store private keys in the app?

No. Only public certificates are stored. A PEM containing a private key is rejected, from the UI as well as from the REST API.

## Why is "Expired" not a status?

Expiration is computed from the `not_after` date (`is_expired`, `days_remaining`) and can be filtered on (`expired`, `expires_within_days`). Statuses describe the lifecycle decided by the users (`Planned`, `Active`, `Revoked`, `Retired`), which is independent from the date.

## Why was the Certificate Authority not filled during the import from PEM?

The import only links a CA whose name is exactly the issuer Common Name of the certificate. If no CA matches, the field is left empty for the user to fill.

## Why was the validation level not filled during the import from PEM?

The validation level is filled only if the certificate contains one of the CA/Browser Forum policy OIDs (DV, OV or EV). Otherwise it is left empty rather than guessed.

## Why can't I delete a Certificate Authority or a Provider?

A Certificate Authority cannot be deleted while it still has issued CAs, and a Provider cannot be deleted while Certificate Authorities still reference it. Reassign or delete the dependent objects first.

## Is the app connected to my CA or certificate vendor?

No. The app is an inventory: it does not issue, renew or retrieve certificates. See [External Interactions](external_interactions.md).
