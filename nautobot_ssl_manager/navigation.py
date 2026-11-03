"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuImportButton, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="SSL Manager",
        icon="shield-check",
        groups=(
            NavMenuGroup(
                name="Certificates",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_ssl_manager:certificate_list",
                        name="Certificates",
                        weight=100,
                        permissions=["nautobot_ssl_manager.view_certificate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_ssl_manager:certificate_add",
                                permissions=["nautobot_ssl_manager.add_certificate"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_ssl_manager:certificate_import_pem",
                                title="Import from PEM",
                                permissions=["nautobot_ssl_manager.add_certificate"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_ssl_manager:certificateauthority_list",
                        name="Certificate Authorities",
                        weight=200,
                        permissions=["nautobot_ssl_manager.view_certificateauthority"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_ssl_manager:certificateauthority_add",
                                permissions=["nautobot_ssl_manager.add_certificateauthority"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_ssl_manager:certificateprovider_list",
                        name="Providers",
                        weight=300,
                        permissions=["nautobot_ssl_manager.view_certificateprovider"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_ssl_manager:certificateprovider_add",
                                permissions=["nautobot_ssl_manager.add_certificateprovider"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
