"""Django API urlpatterns declaration for nautobot_ssl_manager app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_ssl_manager.api import views

router = OrderedDefaultRouter()
router.register("certificate-providers", views.CertificateProviderViewSet)
router.register("certificate-authorities", views.CertificateAuthorityViewSet)

app_name = "nautobot_ssl_manager-api"
urlpatterns = router.urls
