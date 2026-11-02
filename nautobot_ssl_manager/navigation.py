"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

items = (
    NavMenuItem(
        link="plugins:nautobot_ssl_manager:nautobotsslmanagerexamplemodel_list",
        name="Nautobot SSL Manager",
        permissions=["nautobot_ssl_manager.view_nautobotsslmanagerexamplemodel"],
        buttons=(
            NavMenuAddButton(
                link="plugins:nautobot_ssl_manager:nautobotsslmanagerexamplemodel_add",
                permissions=["nautobot_ssl_manager.add_nautobotsslmanagerexamplemodel"],
            ),
        ),
    ),
)

menu_items = (
    NavMenuTab(
        name="Apps",
        groups=(NavMenuGroup(name="Nautobot SSL Manager", items=tuple(items)),),
    ),
)
