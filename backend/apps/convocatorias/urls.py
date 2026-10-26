from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConvocatoriaActivaView, ConvocatoriaSolicitudViewSet

router = DefaultRouter()
router.register("admin/convocatorias", ConvocatoriaSolicitudViewSet, basename="convocatorias-solicitud")

urlpatterns = [
    path("convocatorias/activa/", ConvocatoriaActivaView.as_view(), name="convocatoria-solicitud-activa"),
    *router.urls,
]
