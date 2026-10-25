from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import LogAuditoria
from .serializers import LogAuditoriaSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("usuario", int, description="Id del usuario"),
            OpenApiParameter("accion", str, description="Texto contenido en la acción"),
            OpenApiParameter("modulo", str),
            OpenApiParameter("resultado", str, enum=LogAuditoria.Resultado.values),
            OpenApiParameter("desde", str, description="Fecha inicial (AAAA-MM-DD)"),
            OpenApiParameter("hasta", str, description="Fecha final (AAAA-MM-DD)"),
        ]
    )
)
class LogAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de logs de auditoría. Solo lectura: los logs son inmutables."""

    serializer_class = LogAuditoriaSerializer
    # Provisional: en feature/auth-users se restringe a Superadmin y Jefe CI.
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = LogAuditoria.objects.all()
        params = self.request.query_params

        if usuario := params.get("usuario"):
            qs = qs.filter(usuario_id=usuario)
        if accion := params.get("accion"):
            qs = qs.filter(accion__icontains=accion)
        if modulo := params.get("modulo"):
            qs = qs.filter(modulo=modulo)
        if resultado := params.get("resultado"):
            qs = qs.filter(resultado=resultado)
        if (desde := parse_date(params.get("desde", ""))) is not None:
            qs = qs.filter(created_at__date__gte=desde)
        if (hasta := parse_date(params.get("hasta", ""))) is not None:
            qs = qs.filter(created_at__date__lte=hasta)
        return qs
