# v1.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v1.2.0 (2026-11-17)](https://github.com/HyazOulephant/nautobot-app-ssl-manager/releases/tag/v1.2.0)

### Added

- [#5](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues/5) - Added domain validation tracking: DCV method of a certificate (DNS, HTTP, email, ACME dns-01 / http-01 / tls-alpn-01) and Domain Validation Records (TXT / CNAME records used for validation, such as `_acme-challenge` delegations) linked to certificates, with an optional comparison with Nautobot DNS Models (present, different or absent, computed and never stored) and a link to create a missing record there.
