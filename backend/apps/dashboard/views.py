from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.roles.catalogo import VER
from apps.roles.permissions import PermisoModulo

from . import services


@extend_schema(
    tags=["dashboard"],
    responses=inline_serializer(
        "Dashboard",
        {
            "secciones": serializers.DictField(help_text="Una entrada por módulo que el usuario puede ver."),
            "alertas": serializers.ListField(child=serializers.DictField(), help_text="[{nivel: atencion|aviso|info, texto, enlace}]"),
            "actualizado": serializers.DateTimeField(),
        },
    ),
)
class DashboardView(APIView):
    """Vista ejecutiva por rol, con alertas operativas (RF-030). El panel la consulta cada 60 s."""

    permission_classes = [PermisoModulo]
    modulo = "dashboard"
    acciones_permiso = {"get": VER}

    def get(self, request):
        return Response(services.resumen(request.user))
