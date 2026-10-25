from rest_framework.routers import DefaultRouter

from .views import RolViewSet

router = DefaultRouter()
router.register("admin/roles", RolViewSet, basename="roles")

urlpatterns = router.urls
