from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria import services as auditoria
from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.core.excel import respuesta_excel
from apps.core.pagination import PaginacionEstandar
from apps.core.pdf import respuesta_pdf
from apps.roles.catalogo import APROBAR, EXPORTAR, GENERAR, PUBLICAR, VER
from apps.roles.permissions import PermisoModulo

from . import services
from .models import AjusteOtorgamiento, Otorgamiento
from .serializers import (
    AjustarSerializer,
    AjusteSerializer,
    AnularAjusteSerializer,
    GenerarSerializer,
    OtorgamientoSerializer,
    PublicarSerializer,
    ResultadoSerializer,
)

RESUMEN = inline_serializer(
    "ResumenElegibilidad",
    {
        "solicitudes": serializers.IntegerField(), "elegibles": serializers.IntegerField(), "no_elegibles": serializers.IntegerField(),
        "plazas": serializers.IntegerField(), "motivos": serializers.ListField(child=serializers.DictField()),
    },
)
RESPUESTA_AJUSTE = inline_serializer(
    "RespuestaAjuste", {"ajuste": AjusteSerializer(), "cambios": serializers.ListField(child=serializers.DictField())}
)
PARAMETROS_RESULTADOS = [
    OpenApiParameter("otorgados", bool, description="true: solo con plaza; false: solo sin plaza"),
    OpenApiParameter("elegibles", bool),
    OpenApiParameter("oferta", int),
    OpenApiParameter("buscar", str, description="Nombre del aspirante"),
]


@extend_schema(tags=["otorgamiento"])
class OtorgamientoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Otorgamiento de plazas (RF-057 a RF-064, con las decisiones del cliente).

    - Generar (Secretaría General): primero `previsualizar`, luego `POST` con `confirmar`.
    - Revisar, ajustar y aprobar (Jefe CI); revisar, ajustar y publicar (Vicerrector).
    - Hasta publicar, solo los roles globales ven el resultado; después, cada
      entidad ve lo otorgado en ella.
    """

    serializer_class = OtorgamientoSerializer
    permission_classes = [PermisoModulo]
    modulo = services.MODULO
    # Ajustar y anular exigen además el permiso de la etapa (lo comprueba el service).
    acciones_permiso = {
        "create": GENERAR, "previsualizar": GENERAR, "resultados": VER, "ajustes": VER, "ajustar": VER, "anular_ajuste": VER,
        "aprobar": APROBAR, "publicar": PUBLICAR, "exportar_excel": EXPORTAR, "exportar_pdf": EXPORTAR,
    }
    pagination_class = None

    def get_queryset(self):
        qs = Otorgamiento.objects.select_related("convocatoria", "generado_por", "aprobado_por", "publicado_por")
        if getattr(self, "swagger_fake_view", False) or self.request.user.es_global:
            return qs
        return qs.filter(estado=Otorgamiento.Estado.PUBLICADO)

    def _respuesta(self, otorgamiento, codigo=status.HTTP_200_OK):
        return Response(self.get_serializer(self.get_queryset().get(pk=otorgamiento.pk)).data, status=codigo)

    @extend_schema(parameters=[OpenApiParameter("convocatoria", int, required=True)], responses=RESUMEN)
    @action(detail=False)
    def previsualizar(self, request):
        """Resumen antes de generar: elegibles, no elegibles y motivos."""
        convocatoria = get_object_or_404(ConvocatoriaSolicitud, pk=request.query_params.get("convocatoria") or 0)
        return Response(services.previsualizar(convocatoria))

    @extend_schema(request=GenerarSerializer, responses={201: OtorgamientoSerializer})
    def create(self, request):
        datos = GenerarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._respuesta(services.generar(request.user, datos.validated_data["convocatoria"]), status.HTTP_201_CREATED)

    def _resultados(self, request, otorgamiento):
        qs = services.resultados_visibles(request.user, otorgamiento).prefetch_related("ajustes")
        params = request.query_params
        if (otorgados := params.get("otorgados")) in ("true", "false"):
            qs = qs.filter(otorgada__isnull=otorgados == "false")
        if (elegibles := params.get("elegibles")) in ("true", "false"):
            qs = qs.filter(posicion_ranking__isnull=elegibles == "false")
        if oferta := params.get("oferta"):
            qs = qs.filter(otorgada__oferta_id=oferta)
        if buscar := (params.get("buscar") or "").strip():
            qs = qs.filter(Q(aspirante_nombre__icontains=buscar))
        return qs

    @extend_schema(parameters=PARAMETROS_RESULTADOS, responses=ResultadoSerializer(many=True))
    @action(detail=True)
    def resultados(self, request, pk=None):
        """Ranking y resultado por aspirante (RF-057). Paginado."""
        otorgamiento = self.get_object()
        paginador = PaginacionEstandar()
        pagina = paginador.paginate_queryset(self._resultados(request, otorgamiento), request, view=self)
        return paginador.get_paginated_response(ResultadoSerializer(pagina, many=True).data)

    @extend_schema(responses=AjusteSerializer(many=True))
    @action(detail=True)
    def ajustes(self, request, pk=None):
        """Ediciones manuales con su justificación y lo que cambió en el reparto."""
        otorgamiento = self.get_object()
        if not request.user.es_global:
            return Response([])
        ajustes = otorgamiento.ajustes.select_related("resultado", "usuario", "anulado_por", "opcion__oferta__carrera", "opcion__oferta__facultad", "opcion__oferta__cum_fum")
        return Response(AjusteSerializer(ajustes, many=True).data)

    @extend_schema(request=AjustarSerializer, responses={201: RESPUESTA_AJUSTE})
    @action(detail=True, methods=["post"])
    def ajustar(self, request, pk=None):
        datos = AjustarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ajuste = services.ajustar(request.user, self.get_object(), **datos.validated_data)
        return Response({"ajuste": AjusteSerializer(ajuste).data, "cambios": ajuste.cambios}, status=status.HTTP_201_CREATED)

    @extend_schema(request=AnularAjusteSerializer, responses=RESPUESTA_AJUSTE)
    @action(detail=True, methods=["post"], url_path=r"ajustes/(?P<ajuste_id>\d+)/anular")
    def anular_ajuste(self, request, pk=None, ajuste_id=None):
        datos = AnularAjusteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ajuste = get_object_or_404(AjusteOtorgamiento, pk=ajuste_id, otorgamiento=self.get_object())
        ajuste, cambios = services.anular_ajuste(request.user, ajuste, datos.validated_data["justificacion"])
        return Response({"ajuste": AjusteSerializer(ajuste).data, "cambios": cambios})

    @extend_schema(request=None, responses=OtorgamientoSerializer)
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._respuesta(services.aprobar(request.user, self.get_object()))

    @extend_schema(request=PublicarSerializer, responses=OtorgamientoSerializer)
    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        datos = PublicarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._respuesta(services.publicar(request.user, self.get_object(), datos.validated_data["segunda_convocatoria"]))

    def _filas(self, request, otorgamiento, formato):
        resultados = list(self._resultados(request, otorgamiento))
        auditoria.registrar(
            request=request, accion=f"exportar otorgamiento ({formato})", modulo=services.MODULO,
            entidad_afectada="otorgamiento", entidad_id=otorgamiento.pk, detalle={"registros": len(resultados)},
        )
        return resultados

    @extend_schema(parameters=PARAMETROS_RESULTADOS, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    @action(detail=True, url_path="exportar-excel")
    def exportar_excel(self, request, pk=None):
        """RF-063: resultado del otorgamiento (provisional o publicado, según quién lo pida)."""
        otorgamiento = self.get_object()
        resultados = self._filas(request, otorgamiento, "Excel")
        return respuesta_excel(
            f"otorgamiento-{otorgamiento.convocatoria.anio_academico}-{otorgamiento.convocatoria.numero}.xlsx",
            f"Otorgamiento {otorgamiento.convocatoria.numero}.ª convocatoria {otorgamiento.convocatoria.anio_academico}",
            [("Posición", 9), ("Aspirante", 32), ("Índice", 9), ("Carrera otorgada", 32), ("Entidad", 30), ("Prioridad", 9),
             ("Asignación", 11), ("Motivo de exclusión", 40)],
            [
                [r.posicion_ranking, r.aspirante_nombre, r.indice_utilizado, r.carrera or "No seleccionado", r.entidad, r.prioridad,
                 r.get_tipo_display(), r.motivo_exclusion]
                for r in resultados
            ],
        )

    @extend_schema(parameters=PARAMETROS_RESULTADOS, responses={(200, "application/pdf"): bytes})
    @action(detail=True, url_path="exportar-pdf")
    def exportar_pdf(self, request, pk=None):
        otorgamiento = self.get_object()
        resultados = [r for r in self._filas(request, otorgamiento, "PDF") if r.otorgada_id]
        grupos = {}
        for r in resultados:
            grupos.setdefault((r.carrera, r.entidad), []).append(r)
        convocatoria = otorgamiento.convocatoria
        return respuesta_pdf(
            "otorgamiento/resultado.html",
            {
                "otorgamiento": otorgamiento,
                "grupos": [{"carrera": c, "entidad": e, "resultados": lista} for (c, e), lista in sorted(grupos.items())],
                "publicado_por": otorgamiento.publicado_por.nombre_completo if otorgamiento.publicado_por else "",
            },
            f"otorgamiento-{convocatoria.anio_academico}-{convocatoria.numero}-{timezone.localdate():%Y%m%d}.pdf",
            titulo=f"Otorgamiento de plazas — {convocatoria.numero}.ª convocatoria {convocatoria.anio_academico}",
        )
