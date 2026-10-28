from django.urls import path
from rest_framework.routers import DefaultRouter

from . import publico
from .views import OtorgamientoViewSet

router = DefaultRouter()
router.register("admin/otorgamiento", OtorgamientoViewSet, basename="otorgamiento")

urlpatterns = [
    path("publico/resultados/", publico.ResultadosPublicosView.as_view(), name="resultados-publicos"),
    path("publico/resultados/filtros/", publico.FiltrosResultadosView.as_view(), name="resultados-publicos-filtros"),
    path("publico/resultados/consulta/", publico.ConsultaResultadoView.as_view(), name="resultados-publicos-consulta"),
    *router.urls,
]
