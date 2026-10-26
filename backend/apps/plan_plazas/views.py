from itertools import groupby

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria import services as auditoria
from apps.core.excel import respuesta_excel
from apps.core.exceptions import ErrorDeNegocio
from apps.core.pdf import respuesta_pdf
from apps.nomencladores.models import Carrera, CumFum, Facultad
from apps.roles.catalogo import EDITAR, EXPORTAR, VER
from apps.roles.permissions import PermisoModulo

from . import services
from .models import LineaPlan, PlanPlazas
from .serializers import (
    ComentarioSerializer,
    DecisionSerializer,
    HistorialSerializer,
    LineaSerializer,
    PlanDetalleSerializer,
    PlanSerializer,
    RespuestaEntidadSerializer,
    TextoSerializer,
)

E = PlanPlazas.Estado


def _filtro_entidad(usuario, prefijo=""):
    """Q que limita a la entidad del usuario local (los globales no se filtran)."""
    if usuario.es_global:
        return Q()
    return Q(**{f"{prefijo}facultad": usuario.facultad, f"{prefijo}cum_fum": usuario.cum_fum})


class ForzarSerializer(serializers.Serializer):
    forzar = serializers.BooleanField(default=False)


class ComentarioEntradaSerializer(serializers.Serializer):
    texto = serializers.CharField()
    linea = serializers.IntegerField(required=False, allow_null=True)


@extend_schema(tags=["plan-plazas"])
class PlanViewSet(viewsets.ModelViewSet):
    """Planes de plazas (RF-032 a RF-039). Todos los roles con `plan_plazas.ver` ven los planes;
    los locales, solo las líneas de su entidad. Las transiciones las validan los services."""

    permission_classes = [PermisoModulo]
    modulo = "plan_plazas"
    http_method_names = ["get", "post", "patch", "delete"]
    acciones_permiso = {
        "enviar": EDITAR, "cargar_oferta": EDITAR, "cerrar_revision": EDITAR, "generar_version_final": EDITAR,
        "enviar_propuesta": EDITAR, "complementaria": EDITAR,
        # El Vicerrector no tiene plan_plazas.editar: aprobar es su función; el service valida el rol.
        "aprobar": VER, "devolver": VER,
        "historial": VER, "comentarios": VER, "comentar": EDITAR, "exportar_pdf": EXPORTAR, "exportar_excel": EXPORTAR,
    }

    def get_queryset(self):
        qs = PlanPlazas.objects.select_related("aprobado_por", "complementaria_de")
        if anio := self.request.query_params.get("anio"):
            qs = qs.filter(anio_academico=anio)
        return qs

    def get_serializer_class(self):
        return PlanDetalleSerializer if self.action == "retrieve" else PlanSerializer

    def create(self, request, *args, **kwargs):
        datos = self.get_serializer(data=request.data)
        datos.is_valid(raise_exception=True)
        plan = services.crear_plan(datos.validated_data["anio_academico"], request.user, datos.validated_data.get("notas", ""))
        return Response(PlanDetalleSerializer(plan, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        plan = serializer.instance
        if not services.es_ci(self.request.user):
            raise ErrorDeNegocio("Solo la Comisión de Ingreso edita el plan.")
        if plan.estado == E.PUBLICADO:
            raise ErrorDeNegocio("Un plan publicado no se modifica (RF-039). Crea una versión complementaria.")
        if "anio_academico" in serializer.validated_data and serializer.validated_data["anio_academico"] != plan.anio_academico:
            raise ErrorDeNegocio("El año académico de un plan no se cambia.")
        serializer.save()

    def perform_destroy(self, plan):
        if not services.es_ci(self.request.user) or plan.estado != E.BORRADOR:
            raise ErrorDeNegocio("Solo la Comisión de Ingreso elimina un plan, y solo en borrador.")
        plan.delete()

    def _responder(self, plan):
        plan.refresh_from_db()
        return Response(PlanDetalleSerializer(plan, context=self.get_serializer_context()).data)

    @extend_schema(request=None, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        return self._responder(services.enviar(self.get_object(), request.user))

    @extend_schema(request=None, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"], url_path="cargar-oferta")
    def cargar_oferta(self, request, pk=None):
        plan = self.get_object()
        services.cargar_oferta(plan, request.user)
        return self._responder(plan)

    @extend_schema(request=ForzarSerializer, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"], url_path="cerrar-revision")
    def cerrar_revision(self, request, pk=None):
        datos = ForzarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._responder(services.cerrar_revision(self.get_object(), request.user, datos.validated_data["forzar"]))

    @extend_schema(request=None, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"], url_path="generar-version-final")
    def generar_version_final(self, request, pk=None):
        return self._responder(services.generar_version_final(self.get_object(), request.user))

    @extend_schema(request=TextoSerializer, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"], url_path="enviar-propuesta")
    def enviar_propuesta(self, request, pk=None):
        datos = TextoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        plan = self.get_object()
        services.enviar_propuesta(plan, request.user, datos.validated_data.get("texto", ""))
        return self._responder(plan)

    @extend_schema(request=None, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._responder(services.aprobar(self.get_object(), request.user))

    @extend_schema(request=TextoSerializer, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        datos = TextoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        return self._responder(services.devolver(self.get_object(), request.user, datos.validated_data.get("texto", "")))

    @extend_schema(request=TextoSerializer, responses=PlanDetalleSerializer)
    @action(detail=True, methods=["post"])
    def complementaria(self, request, pk=None):
        datos = TextoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        nuevo = services.crear_complementaria(self.get_object(), request.user, datos.validated_data.get("texto", ""))
        return Response(PlanDetalleSerializer(nuevo, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=HistorialSerializer(many=True))
    @action(detail=True)
    def historial(self, request, pk=None):
        """RF-038. Los roles locales ven los cambios generales y los de sus líneas."""
        plan = self.get_object()
        qs = plan.historial.all()
        if not request.user.es_global:
            qs = qs.filter(Q(linea__isnull=True, descripcion_linea="") | _filtro_entidad(request.user, "linea__"))
        return Response(HistorialSerializer(qs, many=True).data)

    @extend_schema(responses=ComentarioSerializer(many=True))
    @action(detail=True)
    def comentarios(self, request, pk=None):
        qs = self.get_object().comentarios.select_related("usuario__rol", "facultad", "cum_fum", "linea__carrera")
        if not request.user.es_global:
            qs = qs.filter(_filtro_entidad(request.user))
        return Response(ComentarioSerializer(qs, many=True).data)

    @extend_schema(request=ComentarioEntradaSerializer, responses=ComentarioSerializer)
    @comentarios.mapping.post
    def comentar(self, request, pk=None):
        """Comentar exige `plan_plazas.editar` (lo tienen, p. ej., los Jefes de Área)."""
        plan = self.get_object()
        datos = ComentarioEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        linea = None
        if linea_id := datos.validated_data.get("linea"):
            linea = plan.lineas.filter(pk=linea_id).first()
            if linea is None:
                raise ErrorDeNegocio("Esa línea no pertenece al plan.")
        comentario = services.comentar(plan, request.user, datos.validated_data["texto"], linea)
        return Response(ComentarioSerializer(comentario).data, status=status.HTTP_201_CREATED)

    def _lineas_publicadas(self, plan):
        if plan.estado != E.PUBLICADO:
            raise ErrorDeNegocio("Solo se exporta un plan aprobado y publicado (RF-037).")
        lineas = plan.lineas.exclude(plazas_aprobadas=None).select_related("carrera", "facultad", "cum_fum")
        return sorted(lineas.filter(_filtro_entidad(self.request.user)), key=lambda l: (str(l.entidad), l.carrera.nombre))

    def _titulo(self, plan):
        return f"Plan de plazas {plan.anio_academico}" + (" — versión complementaria" if plan.es_complementario else "")

    @extend_schema(responses={(200, "application/pdf"): bytes})
    @action(detail=True, url_path="exportar-pdf")
    def exportar_pdf(self, request, pk=None):
        """PDF con membrete y la marca de aprobación del Vicerrector (RF-037, RE-009)."""
        plan = self.get_object()
        lineas = self._lineas_publicadas(plan)
        grupos = [
            {"entidad": entidad, "lineas": items, "total": sum(l.plazas_aprobadas for l in items)}
            for entidad, grupo in groupby(lineas, key=lambda l: str(l.entidad))
            for items in [list(grupo)]
        ]
        auditoria.registrar(request=request, accion="exportar plan de plazas (PDF)", modulo="plan-plazas", entidad_afectada="plan", entidad_id=plan.pk)
        aprobado_por = (plan.aprobado_por.nombre_completo or plan.aprobado_por.username) if plan.aprobado_por else ""
        return respuesta_pdf(
            "plan_plazas/plan.html",
            {"plan": plan, "grupos": grupos, "total": sum(g["total"] for g in grupos), "aprobado_por": aprobado_por},
            f"plan-plazas-{plan.anio_academico}-v{plan.version}.pdf",
            titulo=self._titulo(plan),
        )

    @extend_schema(responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    @action(detail=True, url_path="exportar-excel")
    def exportar_excel(self, request, pk=None):
        plan = self.get_object()
        lineas = self._lineas_publicadas(plan)
        auditoria.registrar(request=request, accion="exportar plan de plazas (Excel)", modulo="plan-plazas", entidad_afectada="plan", entidad_id=plan.pk)
        aprobacion = f"Aprobado por {plan.aprobado_por} el {plan.fecha_aprobacion:%d/%m/%Y %H:%M}" if plan.aprobado_por else ""
        return respuesta_excel(
            f"plan-plazas-{plan.anio_academico}-v{plan.version}.xlsx",
            titulo=f"{self._titulo(plan)} · versión {plan.version} · {aprobacion}",
            columnas=[("Entidad", 36), ("Tipo", 10), ("Carrera", 36), ("Plazas", 10)],
            filas=[[str(l.entidad), "Facultad" if l.facultad_id else "CUM/FUM", l.carrera.nombre, l.plazas_aprobadas] for l in lineas],
        )


class LineaEntradaSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=PlanPlazas.objects.all())
    carrera = serializers.PrimaryKeyRelatedField(queryset=Carrera.objects.all())
    facultad = serializers.PrimaryKeyRelatedField(queryset=Facultad.objects.all(), required=False, allow_null=True)
    cum_fum = serializers.PrimaryKeyRelatedField(queryset=CumFum.objects.all(), required=False, allow_null=True)
    plazas = serializers.IntegerField(min_value=0)
    comentario = serializers.CharField(required=False, allow_blank=True)


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter("plan", int, required=True), OpenApiParameter("buscar", str)]))
@extend_schema(tags=["plan-plazas"])
class LineaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Líneas de un plan. Quién puede cambiarlas y cómo depende del estado del plan."""

    serializer_class = LineaSerializer
    permission_classes = [PermisoModulo]
    modulo = "plan_plazas"
    http_method_names = ["get", "post", "patch", "delete"]
    pagination_class = None
    acciones_permiso = {"create": EDITAR, "destroy": EDITAR, "responder": EDITAR, "decidir": EDITAR}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LineaPlan.objects.none()
        qs = LineaPlan.objects.select_related("carrera", "facultad", "cum_fum", "plan").filter(_filtro_entidad(self.request.user))
        params = self.request.query_params
        if self.action == "list":
            qs = qs.filter(plan_id=params.get("plan") or 0)
        if buscar := params.get("buscar"):
            qs = qs.filter(carrera__nombre__icontains=buscar)
        return qs

    @extend_schema(request=LineaEntradaSerializer)
    def create(self, request, *args, **kwargs):
        """En borrador, la CI agrega carreras; con el plan enviado, la entidad solicita agregar una (RF-034)."""
        datos = LineaEntradaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        plan = d["plan"]
        if plan.estado == E.BORRADOR:
            linea = services.agregar_linea_ci(plan, d["carrera"], d.get("facultad"), d.get("cum_fum"), d["plazas"], request.user)
        else:
            linea = services.solicitar_carrera(plan, d["carrera"], d["plazas"], d.get("comentario", ""), request.user)
        return Response(self.get_serializer(linea).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if "plazas_propuestas" not in serializer.validated_data:
            raise ErrorDeNegocio("Solo se cambia la propuesta inicial (plazas_propuestas).")
        services.actualizar_linea_ci(serializer.instance, serializer.validated_data["plazas_propuestas"], self.request.user)

    def perform_destroy(self, linea):
        if linea.plan.estado == E.BORRADOR:
            services.quitar_linea_ci(linea, self.request.user)
        else:
            services.retirar_solicitud(linea, self.request.user)

    @extend_schema(request=RespuestaEntidadSerializer, responses=LineaSerializer)
    @action(detail=True, methods=["post"])
    def responder(self, request, pk=None):
        datos = RespuestaEntidadSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        linea = services.responder_linea(self.get_object(), d["accion"], d.get("plazas"), d.get("comentario", ""), request.user)
        return Response(self.get_serializer(linea).data)

    @extend_schema(request=DecisionSerializer, responses=LineaSerializer)
    @action(detail=True, methods=["post"])
    def decidir(self, request, pk=None):
        datos = DecisionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        linea = services.decidir(self.get_object(), d["decision"], d.get("plazas"), d.get("comentario", ""), request.user)
        return Response(self.get_serializer(linea).data)
