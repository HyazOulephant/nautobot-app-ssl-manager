"""Django urlpatterns declaration for nautobot_ssl_manager app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_ssl_manager import views

app_name = "nautobot_ssl_manager"
router = NautobotUIViewSetRouter()

router.register("certificates", views.CertificateUIViewSet)
router.register("certificate-providers", views.CertificateProviderUIViewSet)
router.register("certificate-authorities", views.CertificateAuthorityUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_ssl_manager/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
