from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/configuracion/plantillas", views.PlantillaViewSet, basename="plantillas")

urlpatterns = [
    path("identidad/", views.IdentidadPublicaView.as_view(), name="identidad-publica"),
    path("admin/configuracion/parametros/", views.ParametrosView.as_view(), name="config-parametros"),
    path("admin/configuracion/smtp/", views.SmtpView.as_view(), name="config-smtp"),
    path("admin/configuracion/smtp/probar/", views.ProbarSmtpView.as_view(), name="config-smtp-probar"),
    path("admin/configuracion/identidad/", views.IdentidadView.as_view(), name="config-identidad"),
    *router.urls,
]
