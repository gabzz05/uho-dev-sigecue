from django.urls import path

from . import views

urlpatterns = [
    path("admin/retencion/previsualizar/", views.PrevisualizarRetencionView.as_view(), name="retencion-previsualizar"),
    path("admin/retencion/ejecuciones/", views.EjecucionesRetencionView.as_view(), name="retencion-ejecuciones"),
]
