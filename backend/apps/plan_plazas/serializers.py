from django.db.models import Sum
from rest_framework import serializers

from . import services
from .models import ComentarioPlan, HistorialPlan, LineaPlan, PlanEntidad, PlanPlazas

E = PlanPlazas.Estado


def resumen_entidad(objeto) -> dict:
    entidad = objeto.entidad
    if entidad is None:
        return None
    return {"tipo": "facultad" if objeto.facultad_id else "cum_fum", "id": entidad.pk, "nombre": entidad.nombre}


def acciones_disponibles(plan, usuario):
    """Qué puede hacer el usuario ahora con el plan; el frontend muestra solo esos botones."""
    ci = services.es_ci(usuario)
    acciones = []
    if plan.estado == E.BORRADOR and ci:
        acciones += ["editar_lineas", "cargar_oferta", "enviar", "eliminar"]
    if plan.estado == E.ENVIADO:
        if ci:
            acciones.append("cerrar_revision")
        if services.responde_por_entidad(usuario):
            entidad = plan.entidades.filter(facultad=usuario.facultad, cum_fum=usuario.cum_fum).first()
            if entidad and entidad.estado != PlanEntidad.Estado.PROPUESTA_ENVIADA:
                acciones += ["responder", "enviar_propuesta"]
    if plan.estado == E.REVISION_CI and ci:
        acciones += ["decidir", "generar_version_final"]
    if plan.estado == E.EN_APROBACION and services.es_vicerrector(usuario):
        acciones += ["aprobar", "devolver"]
    if plan.estado == E.PUBLICADO:
        if usuario.tiene_permiso("plan_plazas", "exportar"):
            acciones.append("exportar")
        if ci and services.admite_complementaria(plan):
            acciones.append("crear_complementaria")
    if plan.estado != E.PUBLICADO and usuario.tiene_permiso("plan_plazas", "editar"):
        acciones.append("comentar")
    return acciones


class PlanEntidadSerializer(serializers.ModelSerializer):
    entidad = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    enviada_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = PlanEntidad
        fields = ["id", "entidad", "estado", "estado_nombre", "comentario", "enviada_por_nombre", "enviada_at"]

    def get_entidad(self, objeto) -> dict:
        return resumen_entidad(objeto)

    def get_enviada_por_nombre(self, objeto) -> str:
        return objeto.enviada_por.nombre_completo if objeto.enviada_por else ""


class PlanSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    es_complementario = serializers.BooleanField(read_only=True)
    aprobado_por_nombre = serializers.SerializerMethodField()
    totales = serializers.SerializerMethodField()
    acciones = serializers.SerializerMethodField()

    class Meta:
        model = PlanPlazas
        fields = [
            "id", "anio_academico", "es_complementario", "complementaria_de", "estado", "estado_nombre", "version",
            "notas", "observaciones_vicerrector", "aprobado_por_nombre", "fecha_aprobacion", "created_at", "totales", "acciones",
        ]
        read_only_fields = [
            "complementaria_de", "estado", "version", "observaciones_vicerrector", "fecha_aprobacion", "created_at",
        ]

    def get_aprobado_por_nombre(self, plan) -> str:
        return (plan.aprobado_por.nombre_completo or plan.aprobado_por.username) if plan.aprobado_por else ""

    def _lineas(self, plan):
        lineas = plan.lineas.all()
        usuario = self.context["request"].user
        if not usuario.es_global:
            lineas = lineas.filter(facultad=usuario.facultad, cum_fum=usuario.cum_fum)
        return lineas

    def get_totales(self, plan) -> dict:
        lineas = self._lineas(plan)
        sumas = lineas.aggregate(propuestas=Sum("plazas_propuestas"), aprobadas=Sum("plazas_aprobadas"))
        return {
            "lineas": lineas.count(),
            "plazas_propuestas": sumas["propuestas"] or 0,
            "plazas_aprobadas": sumas["aprobadas"] or 0,
        }

    def get_acciones(self, plan) -> list[str]:
        return acciones_disponibles(plan, self.context["request"].user)


class PlanDetalleSerializer(PlanSerializer):
    entidades = serializers.SerializerMethodField()

    class Meta(PlanSerializer.Meta):
        fields = [*PlanSerializer.Meta.fields, "entidades"]

    def get_entidades(self, plan) -> list[dict]:
        entidades = plan.entidades.select_related("facultad", "cum_fum", "enviada_por")
        usuario = self.context["request"].user
        if not usuario.es_global:
            entidades = entidades.filter(facultad=usuario.facultad, cum_fum=usuario.cum_fum)
        return PlanEntidadSerializer(entidades, many=True).data


class LineaSerializer(serializers.ModelSerializer):
    carrera_nombre = serializers.CharField(source="carrera.nombre", read_only=True)
    entidad = serializers.SerializerMethodField()
    accion_entidad_nombre = serializers.CharField(source="get_accion_entidad_display", read_only=True)
    decision_ci_nombre = serializers.CharField(source="get_decision_ci_display", read_only=True)
    propuesta_entidad = serializers.SerializerMethodField()
    resultado = serializers.SerializerMethodField()

    class Meta:
        model = LineaPlan
        fields = [
            "id", "plan", "carrera", "carrera_nombre", "facultad", "cum_fum", "entidad", "origen",
            "plazas_propuestas", "accion_entidad", "accion_entidad_nombre", "plazas_entidad", "comentario_entidad",
            "propuesta_entidad", "decision_ci", "decision_ci_nombre", "plazas_decision", "comentario_ci", "resultado",
            "plazas_aprobadas",
        ]
        read_only_fields = [
            "origen", "accion_entidad", "plazas_entidad", "comentario_entidad", "decision_ci", "plazas_decision",
            "comentario_ci", "plazas_aprobadas",
        ]
        validators = []

    def get_entidad(self, linea) -> dict:
        return resumen_entidad(linea)

    def get_propuesta_entidad(self, linea) -> int | None:
        return linea.propuesta_de_la_entidad()

    def get_resultado(self, linea) -> int | None:
        """Plazas finales que resultarían con las decisiones actuales."""
        return linea.resultado()


class RespuestaEntidadSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=[LineaPlan.AccionEntidad.ACEPTAR, LineaPlan.AccionEntidad.MODIFICAR, LineaPlan.AccionEntidad.QUITAR])
    plazas = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    comentario = serializers.CharField(required=False, allow_blank=True)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=LineaPlan.DecisionCI.choices)
    plazas = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    comentario = serializers.CharField(required=False, allow_blank=True)


class TextoSerializer(serializers.Serializer):
    texto = serializers.CharField(required=False, allow_blank=True)


class HistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPlan
        fields = ["id", "version", "descripcion_linea", "accion", "valor_anterior", "valor_nuevo", "comentario", "usuario_nombre", "created_at"]


class ComentarioSerializer(serializers.ModelSerializer):
    entidad = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()
    linea_descripcion = serializers.SerializerMethodField()

    class Meta:
        model = ComentarioPlan
        fields = ["id", "entidad", "linea", "linea_descripcion", "texto", "usuario_nombre", "created_at"]
        read_only_fields = ["entidad", "linea_descripcion", "usuario_nombre", "created_at"]

    def get_entidad(self, comentario) -> dict:
        return resumen_entidad(comentario)

    def get_usuario_nombre(self, comentario) -> str:
        usuario = comentario.usuario
        if usuario is None:
            return ""
        rol = f" ({usuario.rol.nombre})" if usuario.rol_id else ""
        return f"{usuario.nombre_completo or usuario.username}{rol}"

    def get_linea_descripcion(self, comentario) -> str:
        return str(comentario.linea) if comentario.linea_id else ""
