from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.aspirantes import services as aspirantes
from apps.aspirantes.models import TipoDocumento
from apps.aspirantes.serializers import DocumentoSerializer
from apps.configuracion.services import parametros
from apps.oferta.models import OfertaCarrera

from . import historial, revision
from .models import EventoHistorial, Observacion, Solicitud, SolicitudCarrera


class OfertaElegibleSerializer(serializers.ModelSerializer):
    """Carrera + entidad que el aspirante puede elegir en la convocatoria."""

    carrera_nombre = serializers.CharField(source="carrera.nombre")
    duracion_anios = serializers.IntegerField(source="carrera.duracion_anios")
    tipo_entidad = serializers.SerializerMethodField()
    entidad_nombre = serializers.CharField(source="entidad.nombre")
    municipio = serializers.CharField(source="entidad.municipio.nombre")
    plazas = serializers.IntegerField(source="plazas_plan")

    class Meta:
        model = OfertaCarrera
        fields = ["id", "carrera", "carrera_nombre", "duracion_anios", "tipo_entidad", "entidad_nombre", "municipio", "plazas"]

    def get_tipo_entidad(self, oferta) -> str:
        return "facultad" if oferta.facultad_id else "cum_fum"


class SolicitudCarreraSerializer(serializers.ModelSerializer):
    oferta = OfertaElegibleSerializer()
    estado_nombre = serializers.CharField(source="get_estado_display")

    class Meta:
        model = SolicitudCarrera
        fields = ["prioridad", "estado", "estado_nombre", "oferta"]


class ObservacionSerializer(serializers.ModelSerializer):
    """Observación tal como la ve el personal: todas, con la entidad autora (RF-055)."""

    elemento = serializers.CharField(read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    entidad_nombre = serializers.SerializerMethodField()
    autor_nombre = serializers.CharField(source="autor.nombre_completo", read_only=True, default=None)
    puede_gestionar = serializers.SerializerMethodField()

    class Meta:
        model = Observacion
        fields = [
            "id", "objetivo", "tipo_documento", "elemento", "texto", "afecta_elegibilidad", "estado", "estado_nombre",
            "entidad_nombre", "autor_nombre", "created_at", "corregida_at", "resuelta_at", "puede_gestionar",
        ]

    def get_entidad_nombre(self, observacion) -> str:
        return str(observacion.entidad) if observacion.entidad else "Comisión de Ingreso"

    def get_puede_gestionar(self, observacion) -> bool:
        return revision.puede_gestionar(self.context["request"].user, observacion)


class ObservacionAspiranteSerializer(serializers.ModelSerializer):
    """Lo que el aspirante necesita para corregir: qué, por qué y en qué estado está."""

    elemento = serializers.CharField(read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Observacion
        fields = ["id", "objetivo", "tipo_documento", "elemento", "texto", "estado", "estado_nombre", "created_at", "corregida_at"]


class SolicitudSerializer(serializers.ModelSerializer):
    convocatoria = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    editable = serializers.BooleanField(read_only=True)
    carreras = SolicitudCarreraSerializer(many=True, read_only=True)
    max_carreras = serializers.SerializerMethodField()
    observaciones = ObservacionAspiranteSerializer(many=True, read_only=True)

    class Meta:
        model = Solicitud
        fields = [
            "id", "convocatoria", "estado", "estado_nombre", "editable", "created_at", "confirmada_at", "modificada_at",
            "carreras", "max_carreras", "observaciones",
        ]

    def get_convocatoria(self, solicitud) -> dict:
        c = solicitud.convocatoria
        return {
            "id": c.pk, "anio_academico": c.anio_academico, "numero": c.numero,
            "fecha_inicio": c.fecha_inicio, "fecha_cierre": c.fecha_cierre, "acepta_solicitudes": c.acepta_solicitudes,
        }

    def get_max_carreras(self, solicitud) -> int:
        return parametros().max_carreras_aspirante


class GuardarCarrerasSerializer(serializers.Serializer):
    ofertas = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, help_text="Ids de OfertaCarrera en orden de prioridad (la primera es la 1)."
    )

    def validate_ofertas(self, ids):
        encontradas = OfertaCarrera.objects.select_related("carrera", "facultad", "cum_fum").in_bulk(ids)
        if faltan := [i for i in ids if i not in encontradas]:
            raise serializers.ValidationError(f"No existe la oferta {faltan[0]}.")
        return [encontradas[i] for i in ids]


# --- Panel administrativo (RF-052 a RF-056) -----------------------------------


def _carreras_visibles(solicitud, usuario):
    """Opciones de la solicitud que ve el usuario: de su entidad si es local (minimización de datos)."""
    carreras = solicitud.carreras.all()
    if usuario.es_global:
        return list(carreras)
    return [
        c for c in carreras
        if (usuario.facultad_id and c.oferta.facultad_id == usuario.facultad_id)
        or (usuario.cum_fum_id and c.oferta.cum_fum_id == usuario.cum_fum_id)
    ]


class SolicitudAdminSerializer(serializers.ModelSerializer):
    """Fila del listado de solicitudes (RF-052)."""

    aspirante_id = serializers.IntegerField(source="aspirante.pk")
    nombre = serializers.CharField(source="aspirante.nombre_completo")
    ci = serializers.CharField(source="aspirante.ci")
    indice_declarado = serializers.DecimalField(
        source="aspirante.perfil_aspirante.indice_declarado", max_digits=5, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    indice_validado = serializers.DecimalField(
        source="aspirante.perfil_aspirante.indice_validado", max_digits=5, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    estado_nombre = serializers.CharField(source="get_estado_display")
    convocatoria = serializers.SerializerMethodField()
    carreras = serializers.SerializerMethodField()
    observaciones_sin_resolver = serializers.IntegerField(read_only=True)

    class Meta:
        model = Solicitud
        fields = [
            "id", "aspirante_id", "nombre", "ci", "indice_declarado", "indice_validado", "estado", "estado_nombre",
            "revision_documental_pendiente", "observaciones_sin_resolver", "convocatoria", "carreras", "confirmada_at", "modificada_at",
        ]

    def get_convocatoria(self, solicitud) -> str:
        return f"{solicitud.convocatoria.numero}.ª {solicitud.convocatoria.anio_academico}"

    @extend_schema_field(SolicitudCarreraSerializer(many=True))
    def get_carreras(self, solicitud):
        return SolicitudCarreraSerializer(_carreras_visibles(solicitud, self.context["request"].user), many=True).data


class SolicitudDetalleAdminSerializer(SolicitudAdminSerializer):
    """Detalle de una solicitud (RF-054): datos del aspirante, documentos, observaciones e historial."""

    aspirante = serializers.SerializerMethodField()
    documentos = serializers.SerializerMethodField()
    observaciones = serializers.SerializerMethodField()
    historial = serializers.SerializerMethodField()
    elegibilidad = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()

    class Meta(SolicitudAdminSerializer.Meta):
        fields = SolicitudAdminSerializer.Meta.fields + [
            "created_at", "aspirante", "documentos", "observaciones", "historial", "elegibilidad", "permisos",
        ]

    def _usuario(self):
        return self.context["request"].user

    def _puede_descargar(self, solicitud):
        if not hasattr(self, "_descarga"):
            self._descarga = aspirantes.puede_ver_documentos(self._usuario(), solicitud.aspirante)
        return self._descarga

    @extend_schema_field(serializers.DictField())
    def get_aspirante(self, solicitud):
        usuario = solicitud.aspirante
        perfil = aspirantes.perfil_de(usuario)
        return {
            "id": usuario.pk, "nombre": usuario.first_name, "apellidos": usuario.last_name, "ci": usuario.ci,
            "email": usuario.email, "celular": usuario.celular, "centro_trabajo": perfil.centro_trabajo,
            "indice_declarado": perfil.indice_declarado, "indice_validado": perfil.indice_validado,
            "indice_validado_por": perfil.indice_validado_por.nombre_completo if perfil.indice_validado_por else None,
            "indice_validado_at": perfil.indice_validado_at,
            "perfil_completo": aspirantes.calcular_perfil_completo(perfil),
            "foto": f"/admin/aspirantes/{usuario.pk}/foto/" if usuario.foto and self._puede_descargar(solicitud) else None,
        }

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_documentos(self, solicitud):
        """Documentos vigentes. Sin el permiso de descarga, se ven sus datos pero no el archivo."""
        vigentes = {d.tipo_id: d for d in aspirantes.perfil_de(solicitud.aspirante).documentos.filter(vigente=True).select_related("tipo")}
        resultado = []
        for tipo in TipoDocumento.objects.filter(activo=True):
            documento = vigentes.get(tipo.pk)
            datos = DocumentoSerializer(documento).data if documento else None
            if datos and not self._puede_descargar(solicitud):
                datos["archivo"] = None
            resultado.append({"tipo": {"id": tipo.pk, "nombre": tipo.nombre, "afecta_elegibilidad": tipo.afecta_elegibilidad}, "documento": datos})
        return resultado

    @extend_schema_field(ObservacionSerializer(many=True))
    def get_observaciones(self, solicitud):
        observaciones = solicitud.observaciones.select_related("facultad", "cum_fum", "autor", "tipo_documento", "solicitud")
        return ObservacionSerializer(observaciones, many=True, context=self.context).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_historial(self, solicitud):
        usuario = self._usuario()
        # Los de esta solicitud y los cambios del perfil hechos sin ninguna solicitud en curso.
        eventos = EventoHistorial.objects.filter(Q(solicitud=solicitud) | Q(aspirante=solicitud.aspirante, solicitud__isnull=True))
        return [
            {
                "id": e.pk, "tipo": e.tipo, "tipo_nombre": e.get_tipo_display(), "descripcion": e.descripcion,
                "usuario": e.usuario.nombre_completo if e.usuario else None, "created_at": e.created_at,
                **historial.visible_para(e, usuario),
            }
            for e in eventos.select_related("usuario").order_by("-created_at", "-id")
        ]

    @extend_schema_field(serializers.DictField())
    def get_elegibilidad(self, solicitud):
        motivos = revision.motivos_no_elegible(solicitud)
        return {"elegible": not motivos, "motivos": motivos}

    @extend_schema_field(serializers.DictField())
    def get_permisos(self, solicitud):
        usuario = self._usuario()
        revisa = revision.puede_revisar(usuario, solicitud) and revision.admite_revision(solicitud)
        perfil = aspirantes.perfil_de(solicitud.aspirante)
        return {
            "revisar": revisa,
            "validar_indice": revisa and (perfil.indice_validado is None or usuario.es_global),
            "descargar_documentos": self._puede_descargar(solicitud),
            "historial_documentos": aspirantes.puede_ver_historial(usuario),
        }


class ValidarIndiceSerializer(serializers.Serializer):
    indice = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)


class CrearObservacionSerializer(serializers.Serializer):
    objetivo = serializers.ChoiceField(Observacion.Objetivo.choices)
    tipo_documento = serializers.PrimaryKeyRelatedField(queryset=TipoDocumento.objects.all(), required=False, allow_null=True)
    texto = serializers.CharField(max_length=2000)
    afecta_elegibilidad = serializers.BooleanField(
        required=False, allow_null=True, default=None,
        help_text="Si se omite: sí para el índice y los documentos marcados (certificación); no para el resto.",
    )


class EditarObservacionSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000, required=False)
    afecta_elegibilidad = serializers.BooleanField(required=False)


class ReabrirObservacionSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=2000, help_text="Por qué no vale la corrección. Se le envía al aspirante.")
