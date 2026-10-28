from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.aspirantes.permissions import EsAspirante
from apps.auditoria import services as auditoria
from apps.convocatorias.services import convocatoria_abierta
from apps.core.excel import respuesta_excel
from apps.core.pdf import respuesta_pdf
from apps.roles.catalogo import EDITAR, EXPORTAR, VER
from apps.roles.permissions import PermisoModulo

from . import consultas, revision, services
from .models import Observacion, Solicitud
from .serializers import (
    CrearObservacionSerializer,
    EditarObservacionSerializer,
    GuardarCarrerasSerializer,
    ObservacionSerializer,
    OfertaElegibleSerializer,
    ReabrirObservacionSerializer,
    SolicitudAdminSerializer,
    SolicitudDetalleAdminSerializer,
    SolicitudSerializer,
    ValidarIndiceSerializer,
)


def _con_carreras(qs):
    return qs.select_related("convocatoria").prefetch_related(
        "carreras__oferta__carrera", "carreras__oferta__facultad__municipio", "carreras__oferta__cum_fum__municipio",
        "observaciones__tipo_documento",
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

    @extend_schema(request=None, responses=SolicitudSerializer)
    @action(detail=True, methods=["post"], url_path="enviar-correccion")
    def enviar_correccion(self, request, pk=None):
        """Da por corregido lo observado (también con la convocatoria cerrada): la solicitud vuelve a Pendiente."""
        return self._respuesta(revision.enviar_correccion(self.get_object()))

    @extend_schema(responses=OfertaElegibleSerializer(many=True))
    @action(detail=False)
    def ofertas(self, request):
        """Carreras que se pueden elegir en la convocatoria abierta (vacío si no hay)."""
        convocatoria = convocatoria_abierta()
        ofertas = services.ofertas_disponibles(convocatoria) if convocatoria else []
        return Response(OfertaElegibleSerializer(ofertas, many=True).data)


PARAMETROS_LISTADO = [
    OpenApiParameter("convocatoria", int),
    OpenApiParameter("carrera", int),
    OpenApiParameter("facultad", int),
    OpenApiParameter("cum_fum", int),
    OpenApiParameter("estado", str, enum=[e for e in Solicitud.Estado.values if e != Solicitud.Estado.BORRADOR]),
    OpenApiParameter("desde", str, description="Fecha de confirmación desde (AAAA-MM-DD)"),
    OpenApiParameter("hasta", str, description="Fecha de confirmación hasta (AAAA-MM-DD)"),
    OpenApiParameter("indice_min", float, description="Índice validado o, si falta, declarado"),
    OpenApiParameter("indice_max", float),
    OpenApiParameter("con_observaciones", bool),
    OpenApiParameter("buscar", str, description="Nombre, apellidos o CI completo"),
    OpenApiParameter("orden", str, enum=["indice", "nombre"]),
]


@extend_schema(tags=["solicitudes"])
class SolicitudAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestión de solicitudes por las entidades (RF-052 a RF-056).

    Cada entidad ve las solicitudes con alguna opción suya y, de ellas, solo sus
    opciones. Ver el detalle (datos personales) queda auditado.
    """

    permission_classes = [PermisoModulo]
    modulo = "solicitudes"
    acciones_permiso = {
        "estadisticas": VER, "exportar_excel": EXPORTAR, "exportar_pdf": EXPORTAR,
        "validar_indice": EDITAR, "observar": EDITAR,
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Solicitud.objects.none()
        return consultas.listado(self.request.user, self.request.query_params)

    def get_serializer_class(self):
        return SolicitudDetalleAdminSerializer if self.action == "retrieve" else SolicitudAdminSerializer

    @extend_schema(parameters=PARAMETROS_LISTADO)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        solicitud = self.get_object()
        auditoria.registrar(request=request, accion="ver solicitud", modulo="solicitudes", entidad_afectada="solicitud", entidad_id=solicitud.pk)
        return Response(self.get_serializer(solicitud).data)

    def _detalle(self, solicitud):
        solicitud = self.get_queryset().get(pk=solicitud.pk)
        return Response(SolicitudDetalleAdminSerializer(solicitud, context=self.get_serializer_context()).data)

    @extend_schema(request=ValidarIndiceSerializer, responses=SolicitudDetalleAdminSerializer)
    @action(detail=True, methods=["post"], url_path="validar-indice")
    def validar_indice(self, request, pk=None):
        datos = ValidarIndiceSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._detalle(revision.validar_indice(request.user, self.get_object(), datos.validated_data["indice"]))

    @extend_schema(request=CrearObservacionSerializer, responses={201: SolicitudDetalleAdminSerializer})
    @action(detail=True, methods=["post"])
    def observar(self, request, pk=None):
        datos = CrearObservacionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        solicitud = self.get_object()
        revision.crear_observacion(request.user, solicitud, **datos.validated_data)
        respuesta = self._detalle(solicitud)
        respuesta.status_code = status.HTTP_201_CREATED
        return respuesta

    @extend_schema(parameters=[OpenApiParameter("convocatoria", int, description="Por defecto, la más reciente")])
    @action(detail=False)
    def estadisticas(self, request):
        """RF-053. El panel lo consulta cada 60 s mientras está visible."""
        convocatoria = consultas.convocatoria_de(request.query_params)
        if convocatoria is None:
            return Response(consultas.estadisticas_vacias())
        return Response(consultas.estadisticas(request.user, convocatoria))

    def _exportacion(self, request, formato):
        solicitudes = list(self.get_queryset())
        filtros = {k: v for k, v in request.query_params.items() if k in {p.name for p in PARAMETROS_LISTADO}}
        # Contiene datos personales: lectura sensible, se audita (RG-010).
        auditoria.registrar(
            request=request, accion=f"exportar solicitudes ({formato})", modulo="solicitudes",
            detalle={"filtros": filtros, "registros": len(solicitudes)},
        )
        return solicitudes, filtros, consultas.filas_exportacion(request.user, solicitudes)

    @extend_schema(parameters=PARAMETROS_LISTADO, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    @action(detail=False, url_path="exportar-excel")
    def exportar_excel(self, request):
        """RF-056: listado con los filtros aplicados."""
        _, _, filas = self._exportacion(request, "Excel")
        return respuesta_excel("solicitudes.xlsx", "Solicitudes de matrícula", consultas.COLUMNAS_EXPORTACION, filas)

    @extend_schema(parameters=PARAMETROS_LISTADO, responses={(200, "application/pdf"): bytes})
    @action(detail=False, url_path="exportar-pdf")
    def exportar_pdf(self, request):
        _, filtros, filas = self._exportacion(request, "PDF")
        texto_filtros = ", ".join(f"{k}: {v}" for k, v in filtros.items())
        return respuesta_pdf(
            "solicitudes/listado.html", {"filas": filas, "filtros": texto_filtros},
            f"solicitudes-{timezone.localdate():%Y%m%d}.pdf", titulo="Solicitudes de matrícula",
        )


@extend_schema(tags=["solicitudes"])
class ObservacionViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Editar, resolver y reabrir observaciones. Cada entidad gestiona solo las suyas (RF-055)."""

    serializer_class = ObservacionSerializer
    permission_classes = [PermisoModulo]
    modulo = "solicitudes"
    acciones_permiso = {"resolver": EDITAR, "reabrir": EDITAR}
    http_method_names = ["patch", "post"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Observacion.objects.none()
        visibles = revision.solicitudes_visibles(self.request.user)
        return Observacion.objects.filter(solicitud__in=visibles).select_related("solicitud", "facultad", "cum_fum", "autor", "tipo_documento")

    def _respuesta(self, observacion):
        observacion = self.get_queryset().get(pk=observacion.pk)
        return Response(ObservacionSerializer(observacion, context=self.get_serializer_context()).data)

    @extend_schema(request=EditarObservacionSerializer, responses=ObservacionSerializer)
    def partial_update(self, request, *args, **kwargs):
        datos = EditarObservacionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._respuesta(revision.editar_observacion(request.user, self.get_object(), **datos.validated_data))

    @extend_schema(request=None, responses=ObservacionSerializer)
    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        return self._respuesta(revision.resolver_observacion(request.user, self.get_object()))

    @extend_schema(request=ReabrirObservacionSerializer, responses=ObservacionSerializer)
    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        datos = ReabrirObservacionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._respuesta(revision.reabrir_observacion(request.user, self.get_object(), datos.validated_data["motivo"]))
