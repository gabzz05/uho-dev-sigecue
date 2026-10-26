from rest_framework.routers import DefaultRouter

from .views import EnvioMasivoViewSet, MisNotificacionesViewSet

router = DefaultRouter()
router.register("notificaciones", MisNotificacionesViewSet, basename="notificaciones")
router.register("admin/notificaciones/envios", EnvioMasivoViewSet, basename="envios-masivos")

urlpatterns = router.urls
