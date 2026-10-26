"""Endpoints públicos de la landing (RF-019 a RF-022). Sin autenticación y sin datos personales."""

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.nomencladores.models import Carrera, CumFum, Facultad, Municipio
from apps.oferta.models import OfertaCarrera

from .. import services
from ..serializers import CarreraPublicaSerializer, ConvocatoriaPublicaSerializer, OfertaPublicaSerializer, RegistroInteresSerializer


class VistaPublica:
    authentication_classes = []
    permission_classes = [AllowAny]


def _ofertas_abiertas():
    convocatoria = services.convocatoria_abierta()
    if convocatoria is None:
        return OfertaCarrera.objects.none()
    return OfertaCarrera.objects.filter(anio_academico=convocatoria.anio_academico, carrera__activo=True).select_related(
        "carrera", "facultad__municipio", "cum_fum__municipio"
    )


@extend_schema(tags=["publico"], responses=inline_serializer("ConvocatoriaInteresActiva", {"convocatoria": ConvocatoriaPublicaSerializer(allow_null=True)}))
class ConvocatoriaActivaView(VistaPublica, APIView):
    """Convocatoria de interés que hoy acepta expresiones de interés; `null` si no hay."""

    def get(self, request):
        convocatoria = services.convocatoria_abierta()
        return Response({"convocatoria": ConvocatoriaPublicaSerializer(convocatoria).data if convocatoria else None})


PARAMETROS_FILTRO = [
    OpenApiParameter("buscar", str),
    OpenApiParameter("duracion", int),
    OpenApiParameter("facultad", int),
    OpenApiParameter("cum_fum", int),
    OpenApiParameter("municipio", int),
]


@extend_schema_view(get=extend_schema(parameters=PARAMETROS_FILTRO, tags=["publico"]))
class OfertaPublicaView(VistaPublica, generics.ListAPIView):
    """Oferta de la convocatoria abierta: una tarjeta por carrera y entidad (RF-019, RF-020)."""

    serializer_class = OfertaPublicaSerializer

    def get_queryset(self):
        qs = _ofertas_abiertas()
        p = self.request.query_params
        if buscar := p.get("buscar"):
            qs = qs.filter(carrera__nombre__icontains=buscar)
        if duracion := p.get("duracion"):
            qs = qs.filter(carrera__duracion_anios=duracion)
        if facultad := p.get("facultad"):
            qs = qs.filter(facultad_id=facultad)
        if cum_fum := p.get("cum_fum"):
            qs = qs.filter(cum_fum_id=cum_fum)
        if municipio := p.get("municipio"):
            qs = qs.filter(Q(facultad__municipio_id=municipio) | Q(cum_fum__municipio_id=municipio))
        return qs.order_by("carrera__nombre", "id")


@extend_schema_view(get=extend_schema(parameters=PARAMETROS_FILTRO[:2], tags=["publico"]))
class CarrerasPublicasView(VistaPublica, generics.ListAPIView):
    """Catálogo de carreras activas, para cuando no hay convocatoria abierta."""

    serializer_class = CarreraPublicaSerializer

    def get_queryset(self):
        qs = Carrera.objects.filter(activo=True)
        p = self.request.query_params
        if buscar := p.get("buscar"):
            qs = qs.filter(nombre__icontains=buscar)
        if duracion := p.get("duracion"):
            qs = qs.filter(duracion_anios=duracion)
        return qs


class DetalleCarreraSerializer(CarreraPublicaSerializer):
    ofertas = serializers.SerializerMethodField()

    class Meta(CarreraPublicaSerializer.Meta):
        fields = [*CarreraPublicaSerializer.Meta.fields, "ofertas"]

    def get_ofertas(self, carrera) -> list[dict]:
        """Dónde se oferta en la convocatoria abierta (vacío si no hay)."""
        return OfertaPublicaSerializer(_ofertas_abiertas().filter(carrera=carrera), many=True, context=self.context).data


@extend_schema(tags=["publico"])
class DetalleCarreraView(VistaPublica, generics.RetrieveAPIView):
    serializer_class = DetalleCarreraSerializer
    queryset = Carrera.objects.filter(activo=True)


@extend_schema(tags=["publico"], responses=inline_serializer("FiltrosPublicos", {
    "facultades": serializers.ListField(child=serializers.DictField()),
    "cum_fum": serializers.ListField(child=serializers.DictField()),
    "municipios": serializers.ListField(child=serializers.DictField()),
}))
class FiltrosPublicosView(VistaPublica, APIView):
    """Opciones de los filtros de la landing (RF-019)."""

    def get(self, request):
        return Response({
            "facultades": list(Facultad.objects.filter(activo=True).values("id", "nombre")),
            "cum_fum": list(CumFum.objects.filter(activo=True).values("id", "nombre", "tipo")),
            "municipios": list(Municipio.objects.filter(activo=True).values("id", "nombre")),
        })


@extend_schema(tags=["publico"], request=RegistroInteresSerializer, responses={201: inline_serializer("InteresRegistrado", {"mensaje": serializers.CharField()})})
class RegistrarInteresView(VistaPublica, APIView):
    """Expresión de interés anónima (RF-021). Limitada por IP para frenar el spam."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "interes"

    def post(self, request):
        datos = RegistroInteresSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        services.registrar_interes(d["oferta"], d["nombre"], d["ci"], d["celular"], d["email"])
        return Response(
            {"mensaje": "Registramos tu interés. Te avisaremos por correo cuando abra la convocatoria oficial."},
            status=status.HTTP_201_CREATED,
        )
