# Uninstall the App from Nautobot

Here you will find any steps necessary to cleanly remove the App from your Nautobot environment.

## Database Cleanup

Prior to removing the app from the `nautobot_config.py`, run the following command to roll back any migration specific to this app.

```shell
nautobot-server migrate nautobot_ssl_manager zero
```

This deletes all the app data (certificates, Certificate Authorities and providers).

The default statuses (`Active`, `Deprecated`, `Retired`, `Planned`, `Revoked`) are **kept**: rolling back the migrations only removes their association with the app models, as these statuses may be used by other models. Delete them manually from *Extensibility > Statuses* if they are no longer needed.

## Remove App configuration

Remove `"nautobot_ssl_manager"` from `PLUGINS` in `nautobot_config.py`.

## Uninstall the package

```bash
pip3 uninstall nautobot-ssl-manager
```
