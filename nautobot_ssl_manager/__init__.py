"""App declaration for nautobot_ssl_manager."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotSslManagerConfig(NautobotAppConfig):
    """App configuration for the nautobot_ssl_manager app."""

    name = "nautobot_ssl_manager"
    verbose_name = "Nautobot SSL Manager"
    version = __version__
    author = "HyazOulephant"
    description = "Nautobot application for SSL/TLS certificate inventory, PKI management and DCV validation."
    base_url = "nautobot-ssl-manager"
    required_settings = []
    default_settings = {}
    docs_view_name = "plugins:nautobot_ssl_manager:docs"
    searchable_models = ["certificateauthority", "certificateprovider"]


config = NautobotSslManagerConfig  # pylint:disable=invalid-name
