from rest_framework.routers import DefaultRouter

from .views import LineaViewSet, PlanViewSet

router = DefaultRouter()
router.register("admin/plan-plazas/lineas", LineaViewSet, basename="lineas-plan")
router.register("admin/plan-plazas", PlanViewSet, basename="plan-plazas")

urlpatterns = router.urls
