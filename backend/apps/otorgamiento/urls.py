from rest_framework.routers import DefaultRouter

from .views import OtorgamientoViewSet

router = DefaultRouter()
router.register("admin/otorgamiento", OtorgamientoViewSet, basename="otorgamiento")

urlpatterns = router.urls
