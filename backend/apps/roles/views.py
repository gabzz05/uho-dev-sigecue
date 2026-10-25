from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ErrorDeNegocio

from .catalogo import ACCIONES, MODULOS, VER
from .models import Permiso, Rol
from .permissions import PermisoModulo
from .serializers import RolSerializer


class RolViewSet(viewsets.ModelViewSet):
    """Roles del sistema y sus permisos por módulo y acción (RE-006)."""

    queryset = Rol.objects.prefetch_related("permisos")
    serializer_class = RolSerializer
    permission_classes = [PermisoModulo]
    modulo = "roles"
    acciones_permiso = {"catalogo": VER}

    def perform_destroy(self, rol):
        if rol.es_sistema:
            raise ErrorDeNegocio("Los roles del sistema no se pueden eliminar; puedes desactivarlos.")
        if rol.usuarios.exists():
            raise ErrorDeNegocio("No se puede eliminar un rol con usuarios asignados.")
        rol.delete()

    @extend_schema(
        responses=inline_serializer(
            "CatalogoPermisos",
            {
                "modulo": serializers.CharField(),
                "nombre": serializers.CharField(),
                "acciones": inline_serializer(
                    "AccionPermiso",
                    {"codigo": serializers.CharField(), "accion": serializers.CharField(), "nombre": serializers.CharField()},
                    many=True,
                ),
            },
            many=True,
        )
    )
    @action(detail=False)
    def catalogo(self, request):
        """Permisos disponibles agrupados por módulo, para construir la matriz en el panel."""
        existentes = {p.codigo for p in Permiso.objects.all()}
        datos = [
            {
                "modulo": modulo,
                "nombre": nombre,
                "acciones": [
                    {"codigo": f"{modulo}.{a}", "accion": a, "nombre": ACCIONES[a]}
                    for a in acciones
                    if f"{modulo}.{a}" in existentes
                ],
            }
            for modulo, (nombre, acciones) in MODULOS.items()
        ]
        return Response(datos)
