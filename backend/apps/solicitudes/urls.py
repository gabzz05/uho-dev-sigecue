from rest_framework.routers import DefaultRouter

from .views import ObservacionViewSet, SolicitudAdminViewSet, SolicitudAspiranteViewSet

router = DefaultRouter()
router.register("solicitudes", SolicitudAspiranteViewSet, basename="solicitudes")
router.register("admin/solicitudes", SolicitudAdminViewSet, basename="solicitudes-admin")
router.register("admin/observaciones", ObservacionViewSet, basename="observaciones")

urlpatterns = router.urls
