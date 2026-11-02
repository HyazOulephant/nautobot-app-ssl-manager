"""Django urlpatterns declaration for nautobot_ssl_manager app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_ssl_manager import views

app_name = "nautobot_ssl_manager"
router = NautobotUIViewSetRouter()

# The standard is for the route to be the hyphenated version of the model class name plural.
# for example, ExampleModel would be example-models.
router.register("nautobot-ssl-manager-example-models", views.NautobotSslManagerExampleModelUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_ssl_manager/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
