from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.configuracion.views import PermisoConfiguracion
from apps.roles.catalogo import EDITAR, VER

from . import services
from .models import RetencionEjecutada


class EjecucionSerializer(serializers.ModelSerializer):
    ejecutada_por = serializers.CharField(source="ejecutada_por.nombre_completo", default=None)

    class Meta:
        model = RetencionEjecutada
        fields = [
            "id", "fecha", "ejecutada_por", "automatica", "aspirantes_anonimizados", "intereses_anonimizados",
            "documentos_eliminados", "espacio_liberado_mb", "duracion_segundos",
        ]


VISTA_PREVIA = inline_serializer(
    "VistaPreviaRetencion",
    {
        "aspirantes": serializers.IntegerField(), "intereses": serializers.IntegerField(), "documentos": serializers.IntegerField(),
        "espacio_mb": serializers.DecimalField(max_digits=12, decimal_places=2), "solo_versiones_antiguas": serializers.IntegerField(),
    },
)


class VistaRetencion:
    """Retención de datos (RG-028): solo el Superadmin la ejecuta; ver exige `configuracion.ver`."""

    permission_classes = [PermisoConfiguracion]
    modulo = "configuracion"
    acciones_permiso = {"get": VER, "post": EDITAR}


@extend_schema(tags=["configuracion"], responses=VISTA_PREVIA)
class PrevisualizarRetencionView(VistaRetencion, APIView):
    """Qué haría una ejecución hoy: aspirantes y expresiones a anonimizar, archivos y espacio que se liberan."""

    def get(self, request):
        return Response(services.previsualizar())


class EjecutarSerializer(serializers.Serializer):
    confirmar = serializers.BooleanField()

    def validate_confirmar(self, valor):
        if not valor:
            raise serializers.ValidationError("Revisa la vista previa y confirma la ejecución.")
        return valor


@extend_schema(tags=["configuracion"])
class EjecucionesRetencionView(VistaRetencion, APIView):
    """Historial de ejecuciones (GET) y ejecución manual adelantada (POST)."""

    @extend_schema(responses=EjecucionSerializer(many=True))
    def get(self, request):
        return Response(EjecucionSerializer(RetencionEjecutada.objects.select_related("ejecutada_por")[:50], many=True).data)

    @extend_schema(request=EjecutarSerializer, responses={201: EjecucionSerializer})
    def post(self, request):
        EjecutarSerializer(data=request.data).is_valid(raise_exception=True)
        ejecucion = services.ejecutar(usuario=request.user)
        return Response(EjecucionSerializer(ejecucion).data, status=status.HTTP_201_CREATED)
