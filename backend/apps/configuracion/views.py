from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.roles.catalogo import EDITAR, VER
from apps.roles.permissions import PermisoModulo

from . import plantillas, services
from .catalogo_plantillas import PLANTILLAS
from .models import ConfiguracionSMTP, IdentidadVisual, PlantillaCorreo
from .serializers import (
    IdentidadSerializer,
    ParametrosSerializer,
    PlantillaSerializer,
    PruebaSmtpSerializer,
    SmtpSerializer,
    VistaPreviaSerializer,
)

MENSAJE = inline_serializer("MensajeConfiguracion", {"mensaje": serializers.CharField()})


class PermisoConfiguracion(PermisoModulo):
    """Leer exige `configuracion.ver`. Modificar, además, ser Superadmin (decisión del cliente)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS or request.user.es_superadmin:
            return True
        self.message = "Solo el Superadmin modifica la configuración del sistema."
        return False


class VistaConfiguracion:
    permission_classes = [PermisoConfiguracion]
    modulo = "configuracion"
    # Vistas que no son ViewSet: el método HTTP es la acción.
    acciones_permiso = {"get": VER, "patch": EDITAR, "post": EDITAR}


class SingletonView(VistaConfiguracion, generics.RetrieveUpdateAPIView):
    """GET y PATCH sobre la única fila de un modelo de configuración."""

    http_method_names = ["get", "patch"]
    modelo = None

    def get_object(self):
        return self.modelo.actual()

    def perform_update(self, serializer):
        serializer.save(actualizado_por=self.request.user)


@extend_schema(tags=["configuracion"])
class ParametrosView(SingletonView):
    """Parámetros del proceso: máximo de carreras (RF-007) y bloqueo de sesión (RF-008)."""

    serializer_class = ParametrosSerializer

    def get_object(self):
        return services.parametros()


@extend_schema(tags=["configuracion"])
class SmtpView(SingletonView):
    """Servidor de correo (RF-009, RE-010)."""

    serializer_class = SmtpSerializer
    modelo = ConfiguracionSMTP


@extend_schema(tags=["configuracion"])
class IdentidadView(SingletonView):
    """Identidad visual: nombre, colores y escudo (RE-001)."""

    serializer_class = IdentidadSerializer
    modelo = IdentidadVisual
    parser_classes = [JSONParser, MultiPartParser, FormParser]


class ProbarSmtpView(VistaConfiguracion, APIView):
    @extend_schema(request=PruebaSmtpSerializer, responses=MENSAJE, tags=["configuracion"])
    def post(self, request):
        datos = PruebaSmtpSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        services.probar_smtp(datos.validated_data["destinatario"])
        return Response({"mensaje": f"Correo de prueba enviado a {datos.validated_data['destinatario']}."})


@extend_schema(tags=["configuracion"])
class PlantillaViewSet(VistaConfiguracion, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Plantillas de correo (RF-011). Se editan; no se crean ni se borran: las define el código."""

    queryset = PlantillaCorreo.objects.all()
    serializer_class = PlantillaSerializer
    lookup_field = "codigo"
    pagination_class = None
    http_method_names = ["get", "patch", "post"]
    acciones_permiso = {"restablecer": EDITAR, "vista_previa": VER}

    def perform_update(self, serializer):
        serializer.save(actualizado_por=self.request.user)

    @extend_schema(request=None, responses=PlantillaSerializer)
    @action(detail=True, methods=["post"])
    def restablecer(self, request, codigo=None):
        """Vuelve al texto por defecto del sistema."""
        plantilla = self.get_object()
        plantilla.asunto = PLANTILLAS[plantilla.codigo]["asunto"]
        plantilla.cuerpo = PLANTILLAS[plantilla.codigo]["cuerpo"]
        plantilla.actualizado_por = request.user
        plantilla.save()
        return Response(self.get_serializer(plantilla).data)

    @extend_schema(request=VistaPreviaSerializer, responses=VistaPreviaSerializer)
    @action(detail=True, methods=["post"], url_path="vista-previa")
    def vista_previa(self, request, codigo=None):
        """Asunto y cuerpo con valores de ejemplo (el nombre de cada variable entre corchetes)."""
        plantilla = self.get_object()
        datos = VistaPreviaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ejemplo = {nombre: f"[{descripcion}]" for nombre, descripcion in PLANTILLAS[plantilla.codigo]["variables"].items()}
        return Response({campo: plantillas.renderizar(datos.validated_data[campo], ejemplo) for campo in ("asunto", "cuerpo")})

    # La vista previa usa POST pero no modifica nada: basta con `configuracion.ver`.
    def get_permissions(self):
        if self.action == "vista_previa":
            return [PermisoModulo()]
        return super().get_permissions()


@extend_schema(responses=IdentidadSerializer, tags=["sistema"])
class IdentidadPublicaView(generics.RetrieveAPIView):
    """Identidad visual para pintar la interfaz (público: la landing también la usa)."""

    serializer_class = IdentidadSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_object(self):
        return IdentidadVisual.actual()
