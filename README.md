# Nautobot SSL Manager

<p align="center">
  <img src="https://raw.githubusercontent.com/HyazOulephant/nautobot-app-ssl-manager/develop/docs/images/icon-nautobot-ssl-manager.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/HyazOulephant/nautobot-app-ssl-manager/actions"><img src="https://github.com/HyazOulephant/nautobot-app-ssl-manager/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://nautobot-app-ssl-manager.readthedocs.io/en/latest/"><img src="https://readthedocs.org/projects/nautobot-app-ssl-manager/badge/"></a>
  <a href="https://pypi.org/project/nautobot-ssl-manager/"><img src="https://img.shields.io/pypi/v/nautobot-ssl-manager"></a>
  <a href="https://pypi.org/project/nautobot-ssl-manager/"><img src="https://img.shields.io/pypi/dm/nautobot-ssl-manager"></a>
  <br>
  An <a href="https://networktocode.com/nautobot-apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

Nautobot SSL Manager turns Nautobot into the source of truth for your SSL/TLS certificates. It adds an inventory of certificates, of the Certificate Authorities (CAs) that issue them and of the providers through which they are obtained, all available from a dedicated **SSL Manager** menu, the REST API and GraphQL.

Certificates are described with the data needed to follow them over their lifecycle: Common Name and Subject Alternative Names, serial number and SHA-256 fingerprint, validity dates, key algorithm and size, validation level, Extended Key Usage, issuing CA, and the certificate they replace when renewed. Expiration is computed from the validity dates, and certificates can be filtered on it (expired, or expiring within N days). A certificate can be created by pasting its PEM: the form is then pre-filled with the data read from the certificate, without guessing anything that the certificate does not contain.

Certificate Authorities are organized as a tree (Root and Intermediate CAs), so the full certification chain of a certificate is visible from its detail view.

Only **public** certificates are stored: private keys are rejected and must never be stored in Nautobot.

> This app is in **beta** (`0.1.0b1`): models and API may still change before `1.0`.

## Documentation

Full documentation for this App can be found on [Read the Docs](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/):

- [User Guide](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/user/app_overview/) - Overview, Getting Started, Using the App, Data Models.
- [Administrator Guide](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/HyazOulephant/nautobot-app-ssl-manager/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://nautobot-app-ssl-manager.readthedocs.io/en/latest/user/faq/) first, then feel free to open an [issue on GitHub](https://github.com/HyazOulephant/nautobot-app-ssl-manager/issues).
