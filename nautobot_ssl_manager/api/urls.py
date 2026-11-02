"""Django API urlpatterns declaration for nautobot_ssl_manager app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_ssl_manager.api import views

router = OrderedDefaultRouter()
# add the name of your api endpoint, usually hyphenated model name in plural, e.g. "my-model-classes"
router.register("nautobot-ssl-manager-example-models", views.NautobotSslManagerExampleModelViewSet)

app_name = "nautobot_ssl_manager-api"
urlpatterns = router.urls
