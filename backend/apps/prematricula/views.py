from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, inline_serializer
from rest_framework import exceptions, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.aspirantes.models import TipoDocumento
from apps.aspirantes.permissions import EsAspirante
from apps.auditoria import services as auditoria
from apps.configuracion.views import PermisoConfiguracion
from apps.core.excel import respuesta_excel
from apps.core.exceptions import ErrorDeNegocio
from apps.core.pdf import respuesta_pdf
from apps.core.validators import TIPO_MIME
from apps.roles.catalogo import CONFIGURAR, EDITAR, EXPORTAR, VER
from apps.roles.permissions import PermisoModulo

from . import services
from .models import ArchivoPrematricula, CampoPrematricula, PeriodoPrematricula, Prematricula
from .serializers import (
    CampoPrematriculaSerializer,
    ConfigurarPeriodoSerializer,
    PeriodoSerializer,
    PrematriculaDetalleSerializer,
    PrematriculaSerializer,
    RevisarSerializer,
    SubirArchivoSerializer,
    TextoPrematriculaSerializer,
)


@extend_schema(tags=["configuracion"])
class CampoPrematriculaViewSet(viewsets.ModelViewSet):
    """Campos y documentos del formulario de prematrícula (RF-010, RF-066). Solo el Superadmin los modifica."""

    queryset = CampoPrematricula.objects.all()
    serializer_class = CampoPrematriculaSerializer
    permission_classes = [PermisoConfiguracion]
    modulo = "configuracion"
    acciones_permiso = {"create": EDITAR, "destroy": EDITAR}
    parser_classes = [JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if (activo := params.get("activo")) in ("true", "false"):
            qs = qs.filter(activo=activo == "true")
        if buscar := params.get("buscar"):
            qs = qs.filter(nombre__icontains=buscar)
        return qs

    def perform_destroy(self, campo):
        if campo.elementos.exists():
            raise ErrorDeNegocio("Ya hay prematrículas con este campo. Desactívalo en lugar de eliminarlo.")
        campo.delete()


# --- Aspirante ---------------------------------------------------------------------


@extend_schema(tags=["aspirante"])
class PrematriculaAspiranteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Prematrícula del aspirante otorgado (RF-065, RF-067): se guarda por partes y se envía."""

    permission_classes = [EsAspirante]
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Prematricula.objects.none()
        return Prematricula.objects.filter(aspirante=self.request.user).select_related(
            "periodo__otorgamiento__convocatoria", "resultado", "aprobado_por", "aspirante"
        )

    def get_serializer_class(self):
        return PrematriculaSerializer if self.action == "list" else PrematriculaDetalleSerializer

    def _detalle(self, prematricula, codigo=status.HTTP_200_OK):
        return Response(PrematriculaDetalleSerializer(self.get_queryset().get(pk=prematricula.pk), context=self.get_serializer_context()).data, status=codigo)

    def _elemento_propio(self, prematricula, elemento):
        if elemento.prematricula_id != prematricula.pk:
            raise exceptions.NotFound()

    @extend_schema(request=TextoPrematriculaSerializer, responses=PrematriculaDetalleSerializer)
    @action(detail=True, methods=["post"])
    def texto(self, request, pk=None):
        prematricula = self.get_object()
        datos = TextoPrematriculaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        self._elemento_propio(prematricula, datos.validated_data["elemento"])
        services.guardar_texto(prematricula, datos.validated_data["elemento"], datos.validated_data["valor"])
        return self._detalle(prematricula)

    @extend_schema(request={"multipart/form-data": SubirArchivoSerializer}, responses={201: PrematriculaDetalleSerializer})
    @action(detail=True, methods=["post"])
    def archivo(self, request, pk=None):
        prematricula = self.get_object()
        datos = SubirArchivoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        elemento = datos.validated_data["elemento"]
        self._elemento_propio(prematricula, elemento)
        services.subir_archivo(prematricula, elemento, datos.validated_data["archivo"], datos.validated_data["formato"])
        return self._detalle(prematricula, status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=PrematriculaDetalleSerializer)
    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        return self._detalle(services.enviar(self.get_object()))


@extend_schema(tags=["prematricula"], responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
class ArchivoPrematriculaView(APIView):
    """Archivo de prematrícula: el aspirante, o el personal con permiso de descarga de la entidad de la plaza. Auditado."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        archivo = get_object_or_404(ArchivoPrematricula.objects.select_related("elemento__prematricula", "elemento__campo"), pk=pk)
        prematricula = archivo.elemento.prematricula
        if not services.puede_descargar(request.user, prematricula) or not archivo.vigente:
            raise exceptions.NotFound()
        auditoria.registrar(
            request=request, accion="descargar archivo de prematrícula", modulo="prematricula",
            entidad_afectada="prematricula", entidad_id=prematricula.pk,
            detalle={
                "motivo": "consulta_documentacion" if request.user.pk == prematricula.aspirante_id else "revision_prematricula",
                "archivo": archivo.nombre_original, "campo": archivo.elemento.campo.nombre, "version": archivo.version,
            },
        )
        nombre = f"{slugify(archivo.elemento.campo.nombre)}-v{archivo.version}.{archivo.archivo.name.rsplit('.', 1)[-1]}"
        return FileResponse(archivo.archivo.open("rb"), content_type=TIPO_MIME[archivo.formato], filename=nombre)


# --- Panel -------------------------------------------------------------------------

PARAMETROS = [
    OpenApiParameter("otorgamiento", int),
    OpenApiParameter("estado", str, enum=Prematricula.Estado.values),
    OpenApiParameter("falta_campo", int, description="Expedientes a los que les falta ese campo (RF-071)"),
    OpenApiParameter("falta_documento", int, description="Expedientes a los que les falta ese documento del perfil"),
    OpenApiParameter("buscar", str, description="Nombre del aspirante"),
]


@extend_schema(tags=["prematricula"])
class PrematriculaAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Panel de prematrícula (RF-068 a RF-072). Cada entidad ve las plazas otorgadas en ella."""

    permission_classes = [PermisoModulo]
    modulo = services.MODULO
    acciones_permiso = {
        "periodos": VER, "faltantes": VER, "configurar_periodo": CONFIGURAR, "revisar": EDITAR, "solicitar_correcciones": EDITAR,
        "aprobar": EDITAR, "exportar_excel": EXPORTAR, "exportar_pdf": EXPORTAR,
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Prematricula.objects.none()
        qs = services.visibles(self.request.user).select_related("aprobado_por")
        params = self.request.query_params
        if otorgamiento := params.get("otorgamiento"):
            qs = qs.filter(periodo__otorgamiento_id=otorgamiento)
        if estado := params.get("estado"):
            qs = qs.filter(estado=estado)
        if buscar := (params.get("buscar") or "").strip():
            qs = qs.filter(Q(resultado__aspirante_nombre__icontains=buscar))
        return services.filtrar_faltante(qs, params.get("falta_campo"), params.get("falta_documento"))

    def get_serializer_class(self):
        return PrematriculaDetalleSerializer if self.action == "retrieve" else PrematriculaSerializer

    @extend_schema(parameters=PARAMETROS)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        prematricula = self.get_object()
        auditoria.registrar(request=request, accion="ver prematrícula", modulo="prematricula", entidad_afectada="prematricula", entidad_id=prematricula.pk)
        return Response(self.get_serializer(prematricula).data)

    def _detalle(self, prematricula):
        return Response(PrematriculaDetalleSerializer(self.get_queryset().get(pk=prematricula.pk), context=self.get_serializer_context()).data)

    @extend_schema(responses=PeriodoSerializer(many=True))
    @action(detail=False)
    def periodos(self, request):
        """Períodos configurados (y otorgamientos publicados sin período, para la Secretaría General)."""
        return Response(PeriodoSerializer(PeriodoPrematricula.objects.select_related("otorgamiento__convocatoria"), many=True).data)

    @extend_schema(
        responses=inline_serializer(
            "OpcionFaltante", {"parametro": serializers.CharField(), "id": serializers.IntegerField(), "nombre": serializers.CharField()}, many=True
        )
    )
    @action(detail=False)
    def faltantes(self, request):
        """Opciones del filtro "le falta…" (RF-071): documentos obligatorios del perfil y campos activos."""
        documentos = [{"parametro": "falta_documento", "id": t.pk, "nombre": t.nombre} for t in TipoDocumento.objects.filter(activo=True, obligatorio=True)]
        campos = [{"parametro": "falta_campo", "id": c.pk, "nombre": c.nombre} for c in CampoPrematricula.objects.filter(activo=True)]
        return Response(documentos + campos)

    @extend_schema(request=ConfigurarPeriodoSerializer, responses={201: PeriodoSerializer})
    @action(detail=False, methods=["post"], url_path="configurar-periodo")
    def configurar_periodo(self, request):
        datos = ConfigurarPeriodoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        periodo = services.configurar_periodo(request.user, **datos.validated_data)
        return Response(PeriodoSerializer(periodo).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=RevisarSerializer, responses=PrematriculaDetalleSerializer)
    @action(detail=True, methods=["post"])
    def revisar(self, request, pk=None):
        datos = RevisarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        prematricula = self.get_object()
        services.revisar_elemento(request.user, prematricula, **datos.validated_data)
        return self._detalle(prematricula)

    @extend_schema(request=None, responses=PrematriculaDetalleSerializer)
    @action(detail=True, methods=["post"], url_path="solicitar-correcciones")
    def solicitar_correcciones(self, request, pk=None):
        return self._detalle(services.solicitar_correcciones(request.user, self.get_object()))

    @extend_schema(request=None, responses=PrematriculaDetalleSerializer)
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._detalle(services.aprobar(request.user, self.get_object()))

    def _filas(self, request, formato):
        prematriculas = list(self.get_queryset())
        auditoria.registrar(
            request=request, accion=f"exportar prematrículas ({formato})", modulo="prematricula",
            detalle={"filtros": dict(request.query_params.items()), "registros": len(prematriculas)},
        )
        return [
            [p.resultado.aspirante_nombre, p.aspirante.ci, p.resultado.carrera, p.resultado.entidad, p.get_estado_display(),
             ", ".join(e.nombre for e in services.faltantes(p)) or "—",
             p.fecha_aprobacion.astimezone().strftime("%d/%m/%Y %H:%M") if p.fecha_aprobacion else "",
             p.aprobado_por.nombre_completo if p.aprobado_por else ""]
            for p in prematriculas
        ]

    @extend_schema(parameters=PARAMETROS, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    @action(detail=False, url_path="exportar-excel")
    def exportar_excel(self, request):
        """RF-072: completos e incompletos, con los filtros aplicados."""
        return respuesta_excel(
            "prematriculas.xlsx", "Prematrículas",
            [("Aspirante", 30), ("CI", 14), ("Carrera", 30), ("Entidad", 28), ("Estado", 16), ("Falta", 40), ("Aprobada", 17), ("Aprobada por", 26)],
            self._filas(request, "Excel"),
        )

    @extend_schema(parameters=PARAMETROS, responses={(200, "application/pdf"): bytes})
    @action(detail=False, url_path="exportar-pdf")
    def exportar_pdf(self, request):
        return respuesta_pdf(
            "prematricula/listado.html", {"filas": self._filas(request, "PDF")},
            f"prematriculas-{timezone.localdate():%Y%m%d}.pdf", titulo="Prematrículas",
        )
