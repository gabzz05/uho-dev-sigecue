from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    responses=inline_serializer("Health", {"status": serializers.CharField()}),
    tags=["sistema"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Comprobación de disponibilidad usada por monitoreo y despliegue."""
    return Response({"status": "ok"})
