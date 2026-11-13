# v1.1 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v1.1.0 (2026-11-13)](https://github.com/HyazOulephant/nautobot-app-ssl-manager/releases/tag/v1.1.0)

### Added

- [#6](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues/6) - Added the CA certificate of a Certificate Authority: optional link to its own Certificate, with consistency checks (basicConstraints, issuer), expiration on the CA views, `has_certificate` / `is_ca_certificate` filters and suggestions when importing a CA certificate from PEM.
- [#7](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues/7) - Added Download menu on the Certificate detail view and REST API endpoint: certificate only (PEM, DER) or with its chain (PEM bundle with or without the Root CA, PKCS#7), built from the CA certificates; incomplete or inconsistent chains are refused.
- [#10](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues/10) - Added import of a PEM bundle (full chain) with a review page: the chain is established by signature verification, existing certificates and CAs are recognized, and the missing CAs and certificates are created after confirmation in a single transaction. A single certificate import now proposes to create its issuing CA when it is not in Nautobot.

### Changed

- [#9](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues/9) - The PEM import identifies the issuing Certificate Authority by signature verification with the stored CA certificates (key identifiers pre-selection): it is pre-selected only when exactly one CA is proven. A CA named like the issuer Common Name is now only an unverified suggestion. The CA edit form suggests the Issued by read from the CA certificate.

### Fixed

- Certification chain panel: each CA is displayed with its CA certificate (status, expiration) or a warning when none is linked, and a CA certificate is displayed under its own CA instead of being duplicated as an extra level. The redundant Certificate Authority, Provider and CA certificate of rows are removed from the Certificate detail panel.
