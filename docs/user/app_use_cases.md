# Using the App

This document describes common use-cases and scenarios for this App.

## General Usage

All the app views are available from the **SSL Manager** menu tab. Each model has the standard Nautobot list, detail, edit, bulk edit/delete and CSV import/export views, and is also available through the [REST API](external_interactions.md#nautobot-rest-api-endpoints) and GraphQL.

## Use-cases and common workflows

### Follow certificate expirations

The certificate list can be filtered on:

- `expired`: certificates whose `not_after` date is in the past;
- `expires_within_days`: certificates not yet expired that expire within the given number of days.

The `days_remaining` and `is_expired` values are computed from `not_after` and exposed in the REST API, which makes them usable by external monitoring or reporting tools.

### Register a certificate from its PEM

*SSL Manager > Certificates > Import from PEM* reads a pasted certificate and opens the creation form pre-filled with the data it contains. Certificates that may be replaced by the new one (same CN or shared SANs, not yet replaced) are suggested next to the *replaces* field. See [Import from PEM](../models/certificate.md#import-from-pem) for the details and the refusal cases.

### Register a full chain at once

Pasting a PEM bundle (certificate and its CA certificates) in *Import from PEM* opens a review page: the chain is established by signature verification, existing objects are recognized, and the missing Certificate Authorities and certificates are proposed for creation, under their issuer. After confirmation, everything is created in a single transaction and the chain can be downloaded right away. See [Import a PEM bundle](../models/certificate.md#import-a-pem-bundle-full-chain).

### Track renewals

A renewed certificate references the certificate it replaces (`replaces`); the previous certificate shows it as *Replaced by*. The `has_replaced_by` filter lists certificates that have (or have not) been replaced, for example to find active certificates that are still waiting for a renewal.

### Find the certificates covering a name

- `san`: certificates whose SAN list contains exactly the given entry (for example `www.example.com`);
- `q` (search): partial match on name, Common Name, serial number, fingerprint, order number, description and comments.

### Explore certification chains

The detail views of a Certificate Authority and of a Certificate show the certification chain from the Root CA. The CA detail view also lists the CAs and the certificates it issued. Certificates can be filtered by CA (`certificate_authority`) or by provider (`provider`, through the CA).

### Deploy a certificate with its chain

When deploying or renewing a certificate on a server or a load balancer, the *Download* menu of the certificate detail view provides the certificate alone (PEM or DER) or with its chain (PEM bundle, or PKCS#7 including the Root CA), built from the CA certificates linked to the Certificate Authorities. The same files are available through the REST API for automation. See [Download](../models/certificate.md#download).
