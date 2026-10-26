from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria import services as auditoria
from apps.core.ambito import filtrar_por_entidad
from apps.core.excel import respuesta_excel
from apps.core.exceptions import ErrorDeNegocio
from apps.oferta.models import OfertaCarrera
from apps.roles.catalogo import EDITAR, EXPORTAR
from apps.roles.permissions import PermisoModulo

from .. import services
from ..models import ConvocatoriaInteres, ExpresionInteres
from ..serializers import ConvocatoriaInteresSerializer, ExpresionInteresSerializer, OfertaSerializer


class SoloGlobalesEscriben:
    """Las convocatorias las crea y gestiona la Comisión de Ingreso (RF-026)."""

    acciones_escritura = ("create", "update", "partial_update", "destroy")

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.action in self.acciones_escritura and not request.user.es_global:
            raise exceptions.PermissionDenied("Las convocatorias de interés las gestiona la Comisión de Ingreso.")


@extend_schema(tags=["interes"])
class ConvocatoriaInteresViewSet(SoloGlobalesEscriben, viewsets.ModelViewSet):
    queryset = ConvocatoriaInteres.objects.all()
    serializer_class = ConvocatoriaInteresSerializer
    permission_classes = [PermisoModulo]
    modulo = "interes"
    acciones_permiso = {"abrir": EDITAR, "cerrar": EDITAR}
    acciones_escritura = ("create", "update", "partial_update", "destroy", "abrir", "cerrar")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.estado == ConvocatoriaInteres.Estado.CERRADA:
            raise ErrorDeNegocio("Una convocatoria cerrada no se puede modificar.")
        serializer.save()

    def perform_destroy(self, convocatoria):
        if convocatoria.estado != ConvocatoriaInteres.Estado.BORRADOR:
            raise ErrorDeNegocio("Solo se puede eliminar una convocatoria en borrador.")
        OfertaCarrera.objects.filter(anio_academico=convocatoria.anio_academico).delete()
        convocatoria.delete()

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def abrir(self, request, pk=None):
        return Response(self.get_serializer(services.abrir(self.get_object())).data)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        return Response(self.get_serializer(services.cerrar(self.get_object())).data)


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter("convocatoria", int), OpenApiParameter("buscar", str)]))
@extend_schema(tags=["interes"])
class OfertaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Oferta de carreras de una convocatoria. Los roles locales ven y gestionan la de su entidad."""

    serializer_class = OfertaSerializer
    permission_classes = [PermisoModulo]
    modulo = "interes"
    # Quitar una carrera de la oferta es editar la convocatoria, no borrar un registro del sistema.
    acciones_permiso = {"destroy": EDITAR}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return OfertaCarrera.objects.none()
        # Meta.ordering no se aplica a consultas con GROUP BY: el orden va explícito.
        qs = (
            OfertaCarrera.objects.select_related("carrera", "facultad__municipio", "cum_fum__municipio")
            .annotate(total_interesados=Count("expresiones_interes"))
            .order_by("carrera__nombre", "id")
        )
        params = self.request.query_params
        if convocatoria := params.get("convocatoria"):
            anio = ConvocatoriaInteres.objects.filter(pk=convocatoria).values_list("anio_academico", flat=True).first()
            qs = qs.filter(anio_academico=anio)
        if buscar := params.get("buscar"):
            qs = qs.filter(carrera__nombre__icontains=buscar)
        return filtrar_por_entidad(qs, self.request.user)

    def create(self, request, *args, **kwargs):
        datos = self.get_serializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        oferta = services.agregar_oferta(d["convocatoria"], d["carrera"], d.get("facultad"), d.get("cum_fum"), request.user)
        oferta.total_interesados = 0
        return Response(self.get_serializer(oferta).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, oferta):
        services.quitar_oferta(oferta, self.request.user)


PARAMETROS_EXPRESIONES = [
    OpenApiParameter("convocatoria", int),
    OpenApiParameter("carrera", int),
    OpenApiParameter("facultad", int),
    OpenApiParameter("cum_fum", int),
    OpenApiParameter("buscar", str, description="Nombre de la persona"),
]


@extend_schema_view(list=extend_schema(parameters=PARAMETROS_EXPRESIONES))
@extend_schema(tags=["interes"])
class ExpresionInteresViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Interesados (RF-031). Contienen datos personales: cada rol ve solo los de su ámbito."""

    serializer_class = ExpresionInteresSerializer
    permission_classes = [PermisoModulo]
    modulo = "interes"
    acciones_permiso = {"exportar": EXPORTAR}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExpresionInteres.objects.none()
        qs = ExpresionInteres.objects.select_related("oferta__carrera", "oferta__facultad", "oferta__cum_fum")
        params = self.request.query_params
        filtros = {"convocatoria": "convocatoria_id", "carrera": "oferta__carrera_id", "facultad": "oferta__facultad_id", "cum_fum": "oferta__cum_fum_id"}
        for parametro, campo in filtros.items():
            if valor := params.get(parametro):
                qs = qs.filter(**{campo: valor})
        if buscar := params.get("buscar"):
            qs = qs.filter(Q(nombre__icontains=buscar))
        return filtrar_por_entidad(qs, self.request.user, campo_facultad="oferta__facultad", campo_cum_fum="oferta__cum_fum")

    @extend_schema(parameters=PARAMETROS_EXPRESIONES, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    @action(detail=False)
    def exportar(self, request):
        """Excel de interesados con nombre, CI, celular, email, carrera, entidad y fecha (RF-031)."""
        expresiones = list(self.get_queryset())
        filtros = {k: v for k, v in request.query_params.items() if k in {p.name for p in PARAMETROS_EXPRESIONES}}
        # Exportación con datos personales: lectura sensible, se audita (RG-010, RG-027).
        auditoria.registrar(
            request=request, accion="exportar interesados", modulo="interes",
            detalle={"filtros": filtros, "registros": len(expresiones)},
        )
        return respuesta_excel(
            "interesados.xlsx",
            titulo="Interesados en carreras por encuentro",
            columnas=[("Nombre", 32), ("CI", 14), ("Celular", 12), ("Email", 30), ("Carrera", 32), ("Entidad", 32), ("Año", 11), ("Fecha", 18)],
            filas=[
                [e.nombre, e.ci, e.celular, e.email, e.oferta.carrera.nombre, str(e.oferta.entidad), e.oferta.anio_academico,
                 e.created_at.astimezone().strftime("%d/%m/%Y %H:%M")]
                for e in expresiones
            ],
        )
