from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ErrorDeNegocio
from apps.roles.catalogo import EDITAR
from apps.roles.permissions import PermisoModulo

from . import services
from .models import ConvocatoriaSolicitud
from .serializers import ConvocatoriaSolicitudPublicaSerializer, ConvocatoriaSolicitudSerializer

E = ConvocatoriaSolicitud.Estado


@extend_schema(tags=["convocatorias"])
class ConvocatoriaSolicitudViewSet(viewsets.ModelViewSet):
    """Convocatorias de solicitud de matrícula (RF-040 a RF-043). Las gestionan los roles globales."""

    queryset = ConvocatoriaSolicitud.objects.prefetch_related("facultades", "cum_fums")
    serializer_class = ConvocatoriaSolicitudSerializer
    permission_classes = [PermisoModulo]
    modulo = "convocatorias"
    acciones_permiso = {"abrir": EDITAR, "cerrar": EDITAR}

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.action in ("create", "update", "partial_update", "destroy", "abrir", "cerrar") and not request.user.es_global:
            raise exceptions.PermissionDenied("Las convocatorias de solicitud las gestiona la Comisión de Ingreso.")

    def create(self, request, *args, **kwargs):
        datos = self.get_serializer(data=request.data)
        datos.is_valid(raise_exception=True)
        convocatoria = services.crear(dict(datos.validated_data), request.user)
        return Response(self.get_serializer(convocatoria).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance.estado == E.CERRADA:
            raise ErrorDeNegocio("Una convocatoria cerrada no se puede modificar.")
        if serializer.instance.estado == E.ABIERTA and ({"facultades", "cum_fums"} & serializer.validated_data.keys()):
            raise ErrorDeNegocio("Las entidades de una convocatoria abierta no se cambian.")
        serializer.save()

    def perform_destroy(self, convocatoria):
        if convocatoria.estado != E.BORRADOR:
            raise ErrorDeNegocio("Solo se puede eliminar una convocatoria en borrador.")
        convocatoria.delete()

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def abrir(self, request, pk=None):
        return Response(self.get_serializer(services.abrir(self.get_object())).data)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        return Response(self.get_serializer(services.cerrar(self.get_object())).data)


@extend_schema(
    tags=["publico"],
    responses=inline_serializer("ConvocatoriaSolicitudActiva", {"convocatoria": ConvocatoriaSolicitudPublicaSerializer(allow_null=True)}),
)
class ConvocatoriaActivaView(APIView):
    """Convocatoria de solicitud que hoy acepta solicitudes; `null` si no hay (RF-023, RF-042)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        convocatoria = services.convocatoria_abierta()
        return Response({"convocatoria": ConvocatoriaSolicitudPublicaSerializer(convocatoria).data if convocatoria else None})
