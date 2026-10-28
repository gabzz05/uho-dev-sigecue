"""Resultados públicos del otorgamiento (RF-063). Sin autenticación.

- El listado muestra solo a los otorgados: nombre, CI enmascarado, carrera,
  entidad y convocatoria. Nunca índice, posición, prioridad ni motivos.
- Se ve mientras no pase `publico_hasta` (cierre de la prematrícula).
- Solo se ve en pantalla: no hay descarga pública.
- La consulta individual por CI completo devuelve el resultado de esa persona.
  Si no hay nada publicado responde siempre el mismo mensaje, exista o no el CI,
  para no servir de mecanismo de enumeración. Tiene límite por IP.
"""

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core import crypto
from apps.core.exceptions import ErrorDeNegocio
from apps.users.validators import validar_ci

from .models import Otorgamiento, ResultadoOtorgamiento

SIN_RESULTADO = "No existe un resultado publicado para los datos introducidos."


def enmascarar_ci(ci):
    """`98042512345` → `*******2345`: solo los 4 últimos dígitos."""
    ci = ci or ""
    return "*" * max(len(ci) - 4, 0) + ci[-4:]


def otorgamientos_visibles():
    hoy = timezone.localdate()
    return Otorgamiento.objects.filter(estado=Otorgamiento.Estado.PUBLICADO).filter(
        Q(publico_hasta__isnull=True) | Q(publico_hasta__gte=hoy)
    )


def _convocatoria(resultado):
    c = resultado.otorgamiento.convocatoria
    return f"{c.numero}.ª convocatoria {c.anio_academico}"


class ResultadoPublicoSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="aspirante_nombre")
    ci = serializers.SerializerMethodField()
    convocatoria = serializers.SerializerMethodField()

    class Meta:
        model = ResultadoOtorgamiento
        fields = ["nombre", "ci", "carrera", "entidad", "convocatoria"]

    def get_ci(self, resultado) -> str:
        return enmascarar_ci(resultado.aspirante.ci)

    def get_convocatoria(self, resultado) -> str:
        return _convocatoria(resultado)


class VistaPublica:
    authentication_classes = []
    permission_classes = [AllowAny]


@extend_schema(
    tags=["publico"],
    parameters=[
        OpenApiParameter("otorgamiento", int, description="Convocatoria (id del otorgamiento publicado)"),
        OpenApiParameter("carrera", str),
        OpenApiParameter("entidad", str),
    ],
)
class ResultadosPublicosView(VistaPublica, generics.ListAPIView):
    """Listado público de otorgados, ordenado por carrera, entidad, apellidos y nombre."""

    serializer_class = ResultadoPublicoSerializer

    def get_queryset(self):
        qs = (
            ResultadoOtorgamiento.objects.filter(otorgamiento__in=otorgamientos_visibles(), otorgada__isnull=False)
            .select_related("aspirante", "otorgamiento__convocatoria")
            .order_by("carrera", "entidad", "aspirante__last_name", "aspirante__first_name", "pk")
        )
        params = self.request.query_params
        if otorgamiento := params.get("otorgamiento"):
            qs = qs.filter(otorgamiento_id=otorgamiento)
        if carrera := params.get("carrera"):
            qs = qs.filter(carrera=carrera)
        if entidad := params.get("entidad"):
            qs = qs.filter(entidad=entidad)
        return qs


@extend_schema(
    tags=["publico"],
    responses=inline_serializer(
        "FiltrosResultados",
        {
            "convocatorias": serializers.ListField(child=serializers.DictField()),
            "carreras": serializers.ListField(child=serializers.CharField()),
            "entidades": serializers.ListField(child=serializers.CharField()),
        },
    ),
)
class FiltrosResultadosView(VistaPublica, APIView):
    """Convocatorias con resultado visible y las carreras y entidades que aparecen en él."""

    def get(self, request):
        visibles = otorgamientos_visibles().select_related("convocatoria").order_by("convocatoria__anio_academico", "convocatoria__numero")
        otorgados = ResultadoOtorgamiento.objects.filter(otorgamiento__in=visibles, otorgada__isnull=False)
        return Response({
            "convocatorias": [
                {"id": o.pk, "nombre": f"{o.convocatoria.numero}.ª convocatoria {o.convocatoria.anio_academico}"} for o in visibles
            ],
            "carreras": sorted(set(otorgados.values_list("carrera", flat=True))),
            "entidades": sorted(set(otorgados.values_list("entidad", flat=True))),
        })


class ConsultaSerializer(serializers.Serializer):
    ci = serializers.CharField(validators=[validar_ci])


@extend_schema(
    tags=["publico"],
    request=ConsultaSerializer,
    responses=inline_serializer(
        "ResultadoIndividual",
        {"resultados": serializers.ListField(child=serializers.DictField(), help_text="[{convocatoria, resultado, carrera, entidad}]")},
    ),
)
class ConsultaResultadoView(VistaPublica, APIView):
    """Consulta del propio resultado por CI completo. POST para que el CI no quede en URLs ni registros."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resultados"

    def post(self, request):
        datos = ConsultaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        resultados = (
            ResultadoOtorgamiento.objects.filter(
                otorgamiento__in=otorgamientos_visibles(), aspirante__ci_hash=crypto.hash_busqueda(datos.validated_data["ci"])
            )
            .select_related("otorgamiento__convocatoria")
            .order_by("otorgamiento__convocatoria__anio_academico", "otorgamiento__convocatoria__numero")
        )
        if not resultados:
            raise ErrorDeNegocio(SIN_RESULTADO)
        return Response({
            "resultados": [
                {
                    "convocatoria": _convocatoria(r),
                    "resultado": "Otorgado" if r.otorgada_id else "No seleccionado",
                    "carrera": r.carrera or None,
                    "entidad": r.entidad or None,
                }
                for r in resultados
            ]
        })
