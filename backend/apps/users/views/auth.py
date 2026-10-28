from django.conf import settings
from django.db import IntegrityError
from django.http import FileResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema, inline_serializer
from rest_framework import exceptions, generics, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps.core.exceptions import ErrorDeNegocio
from apps.users.models import Usuario
from apps.users.serializers import (
    CI_REGISTRADO,
    EMAIL_REGISTRADO,
    ActivacionSerializer,
    CambiarPasswordSerializer,
    LoginSerializer,
    RecuperarPasswordSerializer,
    RegistroSerializer,
    RestablecerPasswordSerializer,
    UsuarioActualSerializer,
)
from apps.users.services import autenticacion, recuperacion, registro

SESION = inline_serializer("Sesion", {"access": serializers.CharField(), "usuario": UsuarioActualSerializer()})
ACCESS = inline_serializer("Access", {"access": serializers.CharField()})
MENSAJE = inline_serializer("Mensaje", {"mensaje": serializers.CharField()})


def _poner_cookie_refresh(response, refresh):
    cookie = settings.AUTH_REFRESH_COOKIE
    response.set_cookie(
        cookie["key"],
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=cookie["path"],
        httponly=cookie["httponly"],
        secure=cookie["secure"],
        samesite=cookie["samesite"],
    )


def _borrar_cookie_refresh(response):
    cookie = settings.AUTH_REFRESH_COOKIE
    response.delete_cookie(cookie["key"], path=cookie["path"], samesite=cookie["samesite"])


class _VistaPublica(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        # Sin esto DRF convierte los 401 en 403 en vistas sin autenticación.
        return 'Bearer realm="api"'


class LoginView(_VistaPublica):
    """Inicia sesión. Devuelve el access token y deja el refresh en una cookie httpOnly."""

    @extend_schema(request=LoginSerializer, responses=SESION, tags=["auth"])
    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = autenticacion.autenticar(
            datos.validated_data["identificador"], datos.validated_data["password"], request=request
        )
        access, refresh = autenticacion.emitir_tokens(usuario)
        request.user = usuario  # Para que la auditoría registre quién inició sesión.
        response = Response(
            {"access": access, "usuario": UsuarioActualSerializer(usuario, context={"request": request}).data}
        )
        _poner_cookie_refresh(response, refresh)
        return response


class RefreshView(_VistaPublica):
    """Renueva el access token usando la cookie de refresh, que también se rota."""

    @extend_schema(request=None, responses=ACCESS, tags=["auth"])
    def post(self, request):
        refresh = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE["key"])
        serializer = TokenRefreshSerializer(data={"refresh": refresh or ""})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, serializers.ValidationError, Usuario.DoesNotExist):
            response = Response(
                {"error": {"codigo": "sesion_expirada", "mensaje": "Tu sesión caducó. Inicia sesión de nuevo."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _borrar_cookie_refresh(response)
            return response

        response = Response({"access": serializer.validated_data["access"]})
        if nuevo := serializer.validated_data.get("refresh"):
            _poner_cookie_refresh(response, nuevo)
        return response


class LogoutView(_VistaPublica):
    """Cierra la sesión: invalida el refresh token y borra la cookie (RG-011)."""

    @extend_schema(request=None, responses={204: None}, tags=["auth"])
    def post(self, request):
        if refresh := request.COOKIES.get(settings.AUTH_REFRESH_COOKIE["key"]):
            autenticacion.revocar(refresh)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _borrar_cookie_refresh(response)
        return response


class RegistroView(_VistaPublica):
    """Registro de aspirantes (RF-013, RF-044). Envía el correo de activación."""

    @extend_schema(request=RegistroSerializer, responses={201: MENSAJE}, tags=["auth"])
    def post(self, request):
        datos = RegistroSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        try:
            registro.registrar_aspirante(
                nombre=d["nombre"], apellidos=d["apellidos"], ci=d["ci"],
                email=d["email"], celular=d["celular"], password=d["password"],
            )
        except IntegrityError as exc:
            # Dos registros simultáneos con el mismo CI o correo pasan juntos la validación.
            campo, mensaje = ("ci", CI_REGISTRADO) if "ci_hash" in str(exc) else ("email", EMAIL_REGISTRADO)
            raise serializers.ValidationError({campo: [mensaje]})
        return Response(
            {"mensaje": "Te enviamos un correo para activar tu cuenta. Revisa tu bandeja de entrada."},
            status=status.HTTP_201_CREATED,
        )


class ActivarView(_VistaPublica):
    """Activa la cuenta con el token recibido por correo (RF-045)."""

    @extend_schema(request=ActivacionSerializer, responses=MENSAJE, tags=["auth"])
    def post(self, request):
        datos = ActivacionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        registro.activar_cuenta(datos.validated_data["token"])
        return Response({"mensaje": "Tu cuenta está activa. Ya puedes iniciar sesión."})


class RecuperarPasswordView(_VistaPublica):
    """Envía al correo un enlace para restablecer la contraseña.

    Responde lo mismo exista o no la cuenta, para no revelar qué correos están registrados.
    """

    @extend_schema(request=RecuperarPasswordSerializer, responses=MENSAJE, tags=["auth"])
    def post(self, request):
        datos = RecuperarPasswordSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        recuperacion.solicitar(datos.validated_data["email"])
        return Response(
            {
                "mensaje": "Si el correo pertenece a una cuenta de SIGECUE, te enviamos un enlace para "
                f"restablecer la contraseña. Es válido durante {recuperacion.horas_validez()} horas."
            }
        )


class RestablecerPasswordView(_VistaPublica):
    """Fija la contraseña nueva con el enlace recibido por correo y cierra las sesiones abiertas."""

    @extend_schema(request=RestablecerPasswordSerializer, responses=MENSAJE, tags=["auth"])
    def post(self, request):
        datos = RestablecerPasswordSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = datos.validated_data["usuario"]
        recuperacion.restablecer(usuario, datos.validated_data["token"], datos.validated_data["password"])
        request.user = usuario  # Para que la auditoría registre quién la cambió.
        return Response({"mensaje": "Tu contraseña se cambió. Ya puedes iniciar sesión con la nueva."})


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """Perfil del usuario autenticado, con su rol y permisos."""

    serializer_class = UsuarioActualSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        usuario = serializer.save()
        if usuario.es_aspirante and "foto" in serializer.validated_data:
            from apps.aspirantes import services as aspirantes

            aspirantes.foto_cambiada(usuario)


@extend_schema(tags=["auth"], responses={(200, "image/*"): OpenApiTypes.BINARY})
class MiFotoView(APIView):
    """Foto de perfil del usuario autenticado (está en el almacenamiento privado)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.foto:
            raise exceptions.NotFound()
        return FileResponse(request.user.foto.open("rb"))


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CambiarPasswordSerializer, responses={204: None}, tags=["auth"])
    def post(self, request):
        if request.user.origen == Usuario.Origen.SGU:
            raise ErrorDeNegocio("Tu contraseña se gestiona en el Sistema de Gestión de Usuarios de la UHO.")
        datos = CambiarPasswordSerializer(data=request.data, context={"request": request})
        datos.is_valid(raise_exception=True)
        request.user.set_password(datos.validated_data["nueva"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
