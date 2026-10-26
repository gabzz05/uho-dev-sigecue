from rest_framework.routers import DefaultRouter

from .views import SolicitudAspiranteViewSet

router = DefaultRouter()
router.register("solicitudes", SolicitudAspiranteViewSet, basename="solicitudes")

urlpatterns = router.urls
