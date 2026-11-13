# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First steps with the App

Once installed, the app adds an **SSL Manager** tab to the navigation menu. The recommended order to populate the inventory follows the dependencies between the models:

1. **Create the providers** (*SSL Manager > Providers*): the vendors or services through which you obtain certificates. This step is optional, a CA can exist without provider.
2. **Create the Certificate Authorities** (*SSL Manager > Certificate Authorities*), starting with the Root CAs, then the Intermediate CAs with their *Issued by* field set to the issuing CA. Set the type (`public` or `private`) and, if relevant, the provider.
3. **Add the certificates** (*SSL Manager > Certificates*):
    - either with **Import from PEM**: paste the public certificate, check the pre-filled form, then complete the fields that cannot be read from the certificate (status, auto-renew, order number, tenant, replaced certificate);
    - or with **Import from PEM** and a full chain (PEM bundle): a review page proposes to create the missing Certificate Authorities and certificates at once, which also covers step 2;
    - or with the standard **Add** form, or a CSV import.

!!! tip
    The import from PEM pre-selects the Certificate Authority of a certificate only when it is proven by signature, which requires the CA certificate (with its PEM) to be linked to the CA. Import and link the CA certificates first, or import the full chain (PEM bundle), and the CA of the next certificates will be found whatever the CA name.

## What are the next steps?

- Use the `expires_within_days` and `expired` filters to follow upcoming expirations, from the UI or the REST API.
- When a certificate is renewed, create the new certificate with *replaces* set to the previous one, then change the status of the previous one: the renewal history stays visible on both certificates.
- Assign tenants, tags, contacts or teams to organize ownership.

You can check out the [Use Cases](app_use_cases.md) section for more examples.
