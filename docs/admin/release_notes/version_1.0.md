# v1.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v1.0.0 (2026-11-04)](https://github.com/HyazOulephant/nautobot-app-ssl-manager/releases/tag/v1.0.0)

### Added

- Added certification chains: Certificate Authorities can be issued by another CA (Root / Intermediate deduced from the tree), with a tree list view and a certification chain panel on CA and Certificate detail views.
- Added the Certificate model, with SANs, validity, renewal chain (replaces), Extended Key Usage and an import from PEM.
- Certificate models added: CertificateProvider and CertificateAuthority, under the new SSL Manager navigation menu.

### Fixed

- Fixed the rendering of Subject Alternative Names and Extended Key Usage on the certificate detail view (the line separator was displayed as text).

### Documentation

- Replaced the documentation template placeholders with the app documentation (overview, getting started, use cases, REST API, FAQ, install/upgrade/uninstall, architecture decisions).
