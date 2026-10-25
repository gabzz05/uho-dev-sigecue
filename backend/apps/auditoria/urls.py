from rest_framework.routers import DefaultRouter

from .views import LogAuditoriaViewSet

router = DefaultRouter()
router.register("admin/logs", LogAuditoriaViewSet, basename="logs")

urlpatterns = router.urls
