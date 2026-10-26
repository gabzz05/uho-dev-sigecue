from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/tipos-documento", views.TipoDocumentoViewSet, basename="tipos-documento")

urlpatterns = [
    path("aspirante/perfil/", views.PerfilAspiranteView.as_view(), name="aspirante-perfil"),
    path("aspirante/documentos/", views.SubirDocumentoView.as_view(), name="aspirante-documentos"),
    path("documentos/<int:pk>/archivo/", views.ArchivoDocumentoView.as_view(), name="documento-archivo"),
    path("admin/aspirantes/<int:usuario_id>/documentos/", views.DocumentosAspiranteView.as_view(), name="aspirante-documentos-admin"),
    path("admin/aspirantes/<int:usuario_id>/foto/", views.FotoAspiranteView.as_view(), name="aspirante-foto-admin"),
    *router.urls,
]
