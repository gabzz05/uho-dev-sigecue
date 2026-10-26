from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import admin, publico

router = DefaultRouter()
router.register("admin/interes/convocatorias", admin.ConvocatoriaInteresViewSet, basename="convocatorias-interes")
router.register("admin/interes/ofertas", admin.OfertaViewSet, basename="ofertas-interes")
router.register("admin/interes/expresiones", admin.ExpresionInteresViewSet, basename="expresiones-interes")

urlpatterns = [
    # Públicos (landing)
    path("interes/", publico.RegistrarInteresView.as_view(), name="registrar-interes"),
    path("interes/convocatoria/", publico.ConvocatoriaActivaView.as_view(), name="convocatoria-interes-activa"),
    path("oferta/", publico.OfertaPublicaView.as_view(), name="oferta-publica"),
    path("carreras/", publico.CarrerasPublicasView.as_view(), name="carreras-publicas"),
    path("carreras/<int:pk>/", publico.DetalleCarreraView.as_view(), name="carrera-publica"),
    path("publico/filtros/", publico.FiltrosPublicosView.as_view(), name="filtros-publicos"),
    *router.urls,
]
