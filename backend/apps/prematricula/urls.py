from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("prematricula", views.PrematriculaAspiranteViewSet, basename="prematricula")
router.register("admin/prematricula", views.PrematriculaAdminViewSet, basename="prematricula-admin")
router.register("admin/campos-prematricula", views.CampoPrematriculaViewSet, basename="campos-prematricula")

urlpatterns = [
    path("prematricula/archivos/<int:pk>/", views.ArchivoPrematriculaView.as_view(), name="prematricula-archivo"),
    *router.urls,
]
