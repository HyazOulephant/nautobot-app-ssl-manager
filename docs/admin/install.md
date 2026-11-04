# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 3.1.0 and higher (Nautobot 3.x).
- Databases supported: PostgreSQL, MySQL.
- Python dependency installed with the app: [`cryptography`](https://cryptography.io/) (>= 46.0.7), used to parse PEM certificates.

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix.

### Access Requirements

The app does not need access to any external system.

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`nautobot-ssl-manager`](https://pypi.org/project/nautobot-ssl-manager/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-ssl-manager
```

!!! note
    While the app is in beta, `pip` only installs pre-releases when asked explicitly: use `pip install --pre nautobot-ssl-manager` or pin the version (for example `nautobot-ssl-manager==0.1.0b1`).

To ensure Nautobot SSL Manager is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-ssl-manager` package:

```shell
echo nautobot-ssl-manager >> local_requirements.txt
```

Once installed, the app needs to be enabled in your Nautobot configuration by appending `"nautobot_ssl_manager"` to the `PLUGINS` list in your `nautobot_config.py` file:

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_ssl_manager"]
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration

The app does not have any setting: no `PLUGINS_CONFIG` entry is required.

## Permissions

The app uses the standard Nautobot object permissions on its models (`nautobot_ssl_manager.<action>_certificate`, `..._certificateauthority`, `..._certificateprovider`, with `view`, `add`, `change` and `delete` actions). The *Import from PEM* view requires the `add_certificate` permission.
