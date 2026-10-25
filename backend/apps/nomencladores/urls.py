from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
for ruta, vista in [
    ("municipios", views.MunicipioViewSet),
    ("facultades", views.FacultadViewSet),
    ("cum-fum", views.CumFumViewSet),
    ("areas", views.AreaViewSet),
    ("departamentos", views.DepartamentoViewSet),
    ("cargos", views.CargoViewSet),
    ("carreras", views.CarreraViewSet),
]:
    router.register(f"admin/nomencladores/{ruta}", vista, basename=f"nomenclador-{ruta}")

urlpatterns = router.urls
