from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import admin, auth

router = DefaultRouter()
router.register("admin/usuarios", admin.UsuarioViewSet, basename="usuarios")

urlpatterns = [
    path("auth/login/", auth.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", auth.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", auth.LogoutView.as_view(), name="auth-logout"),
    path("auth/registro/", auth.RegistroView.as_view(), name="auth-registro"),
    path("auth/activar/", auth.ActivarView.as_view(), name="auth-activar"),
    path("auth/me/", auth.MeView.as_view(), name="auth-me"),
    path("auth/me/foto/", auth.MiFotoView.as_view(), name="auth-me-foto"),
    path("auth/me/password/", auth.CambiarPasswordView.as_view(), name="auth-password"),
    *router.urls,
]
