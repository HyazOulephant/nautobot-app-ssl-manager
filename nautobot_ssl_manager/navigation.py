"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="SSL Manager",
        icon="shield-check",
        groups=(
            NavMenuGroup(
                name="Certificate Authorities",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_ssl_manager:certificateauthority_list",
                        name="Certificate Authorities",
                        weight=100,
                        permissions=["nautobot_ssl_manager.view_certificateauthority"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_ssl_manager:certificateauthority_add",
                                permissions=["nautobot_ssl_manager.add_certificateauthority"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Providers",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_ssl_manager:certificateprovider_list",
                        name="Certificate Providers",
                        weight=100,
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
