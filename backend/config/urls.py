from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1 = [
    path("", include("apps.core.urls")),
    path("", include("apps.auditoria.urls")),
    path("", include("apps.roles.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.nomencladores.urls")),
    path("", include("apps.configuracion.urls")),
    path("", include("apps.notificaciones.urls")),
    path("", include("apps.interes.urls")),
    path("", include("apps.plan_plazas.urls")),
    path("", include("apps.convocatorias.urls")),
    path("", include("apps.aspirantes.urls")),
    path("", include("apps.solicitudes.urls")),
]

urlpatterns = [
    # /admin es el panel de React; el admin de Django queda en otra ruta.
    path("django-admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    # En producción las imágenes públicas las sirve nginx.
    urlpatterns += static(settings.PUBLIC_MEDIA_URL, document_root=settings.PUBLIC_MEDIA_ROOT)
