from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.aspirantes.permissions import EsAspirante
from apps.convocatorias.services import convocatoria_abierta

from . import services
from .models import Solicitud
from .serializers import GuardarCarrerasSerializer, OfertaElegibleSerializer, SolicitudSerializer


def _con_carreras(qs):
    return qs.select_related("convocatoria").prefetch_related(
        "carreras__oferta__carrera", "carreras__oferta__facultad__municipio", "carreras__oferta__cum_fum__municipio"
    )


@extend_schema(tags=["aspirante"])
class SolicitudAspiranteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Solicitudes del aspirante autenticado (RF-047 a RF-051).

    - `POST /solicitudes/`: crea (o devuelve) el borrador en la convocatoria abierta.
    - `PUT /solicitudes/{id}/carreras/`: reemplaza la selección, en orden de prioridad.
    - `POST /solicitudes/{id}/confirmar/`: la presenta oficialmente (pasa a Pendiente).
    """

    serializer_class = SolicitudSerializer
    permission_classes = [EsAspirante]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Solicitud.objects.none()
        return _con_carreras(Solicitud.objects.filter(aspirante=self.request.user))

    def _respuesta(self, solicitud, codigo=status.HTTP_200_OK):
        return Response(self.get_serializer(_con_carreras(Solicitud.objects.all()).get(pk=solicitud.pk)).data, status=codigo)

    @extend_schema(request=None, responses={201: SolicitudSerializer})
    def create(self, request):
        return self._respuesta(services.obtener_o_crear(request.user), status.HTTP_201_CREATED)

    @extend_schema(request=GuardarCarrerasSerializer, responses=SolicitudSerializer)
    @action(detail=True, methods=["put"])
    def carreras(self, request, pk=None):
        datos = GuardarCarrerasSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._respuesta(services.guardar_carreras(self.get_object(), datos.validated_data["ofertas"]))

    @extend_schema(request=None, responses=SolicitudSerializer)
    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        return self._respuesta(services.confirmar(self.get_object()))

    @extend_schema(responses=OfertaElegibleSerializer(many=True))
    @action(detail=False)
    def ofertas(self, request):
        """Carreras que se pueden elegir en la convocatoria abierta (vacío si no hay)."""
        convocatoria = convocatoria_abierta()
        ofertas = services.ofertas_disponibles(convocatoria) if convocatoria else []
        return Response(OfertaElegibleSerializer(ofertas, many=True).data)
