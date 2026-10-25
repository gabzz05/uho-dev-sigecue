from django.db.models import ProtectedError, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.core.ambito import filtrar_por_entidad
from apps.core.exceptions import ErrorDeNegocio
from apps.roles.permissions import PermisoModulo

from . import serializers as s
from .models import Area, Cargo, Carrera, CumFum, Departamento, Facultad, Municipio

PARAMETROS_COMUNES = [
    OpenApiParameter("activo", bool),
    OpenApiParameter("buscar", str, description="Texto contenido en el nombre o el código"),
]


class NomencladorViewSet(viewsets.ModelViewSet):
    """CRUD común de los nomencladores (RE-005).

    - Lectura: cualquier rol con `nomencladores.ver`.
    - Escritura: además de `nomencladores.crear/editar/eliminar`, los catálogos
      globales solo los modifican los roles globales (`solo_globales_escriben`).
    - Borrar un registro en uso no se permite: hay que desactivarlo.
    - `filtros`: parámetros de consulta admitidos → campo del modelo.
    """

    permission_classes = [PermisoModulo]
    modulo = "nomencladores"
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    solo_globales_escriben = True
    campos_busqueda = ["nombre"]
    filtros = {}

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if (activo := params.get("activo")) in ("true", "false"):
            qs = qs.filter(activo=activo == "true")
        if buscar := params.get("buscar"):
            condicion = Q()
            for campo in self.campos_busqueda:
                condicion |= Q(**{f"{campo}__icontains": buscar})
            qs = qs.filter(condicion)
        for parametro, campo in self.filtros.items():
            if valor := params.get(parametro):
                qs = qs.filter(**{campo: valor})
        return qs

    def check_permissions(self, request):
        super().check_permissions(request)
        # Antes de validar los datos: sin permiso la respuesta es 403, no 400.
        escribe = self.action in ("create", "update", "partial_update", "destroy")
        if escribe and self.solo_globales_escriben and not request.user.es_global:
            raise exceptions.PermissionDenied("Este catálogo lo gestiona la Comisión de Ingreso.")

    def perform_destroy(self, instancia):
        try:
            instancia.delete()
        except ProtectedError:
            raise ErrorDeNegocio("Este registro está en uso y no se puede eliminar. Puedes desactivarlo.")


def _documentar(*parametros):
    return extend_schema_view(list=extend_schema(parameters=[*PARAMETROS_COMUNES, *parametros]))


@_documentar()
class MunicipioViewSet(NomencladorViewSet):
    queryset = Municipio.objects.all()
    serializer_class = s.MunicipioSerializer


@_documentar(OpenApiParameter("municipio", int))
class FacultadViewSet(NomencladorViewSet):
    queryset = Facultad.objects.select_related("municipio")
    serializer_class = s.FacultadSerializer
    campos_busqueda = ["nombre", "codigo"]
    filtros = {"municipio": "municipio_id"}


@_documentar(OpenApiParameter("municipio", int), OpenApiParameter("tipo", str, enum=CumFum.Tipo.values))
class CumFumViewSet(NomencladorViewSet):
    queryset = CumFum.objects.select_related("municipio")
    serializer_class = s.CumFumSerializer
    campos_busqueda = ["nombre", "codigo"]
    filtros = {"municipio": "municipio_id", "tipo": "tipo"}


@_documentar(OpenApiParameter("facultad", int), OpenApiParameter("cum_fum", int))
class AreaViewSet(NomencladorViewSet):
    """Las áreas son de cada entidad: los roles locales ven y gestionan solo las suyas."""

    queryset = Area.objects.select_related("facultad", "cum_fum")
    serializer_class = s.AreaSerializer
    solo_globales_escriben = False
    filtros = {"facultad": "facultad_id", "cum_fum": "cum_fum_id"}

    def get_queryset(self):
        return filtrar_por_entidad(super().get_queryset(), self.request.user)


@_documentar(OpenApiParameter("area", int))
class DepartamentoViewSet(NomencladorViewSet):
    queryset = Departamento.objects.select_related("area")
    serializer_class = s.DepartamentoSerializer
    solo_globales_escriben = False
    filtros = {"area": "area_id"}

    def get_queryset(self):
        return filtrar_por_entidad(
            super().get_queryset(), self.request.user, campo_facultad="area__facultad", campo_cum_fum="area__cum_fum"
        )


@_documentar()
class CargoViewSet(NomencladorViewSet):
    queryset = Cargo.objects.all()
    serializer_class = s.CargoSerializer


@_documentar(OpenApiParameter("duracion", int, description="Duración en años"))
class CarreraViewSet(NomencladorViewSet):
    queryset = Carrera.objects.all()
    serializer_class = s.CarreraSerializer
    campos_busqueda = ["nombre", "codigo"]
    filtros = {"duracion": "duracion_anios"}
