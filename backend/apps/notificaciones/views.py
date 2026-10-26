from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.ambito import filtrar_por_entidad
from apps.roles.catalogo import CREAR
from apps.roles.permissions import PermisoModulo

from . import services
from .models import EnvioMasivo, Notificacion
from .serializers import EnvioMasivoSerializer, GrupoSerializer, NotificacionSerializer

CONTADOR = inline_serializer("ContadorNotificaciones", {"no_leidas": serializers.IntegerField()})


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter("leida", bool)]))
@extend_schema(tags=["notificaciones"])
class MisNotificacionesViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Notificaciones del usuario autenticado (RF-073, RF-074). Cada uno ve solo las suyas."""

    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notificacion.objects.none()
        qs = Notificacion.objects.filter(usuario=self.request.user)
        if (leida := self.request.query_params.get("leida")) in ("true", "false"):
            qs = qs.filter(leida=leida == "true")
        return qs

    @extend_schema(responses=CONTADOR)
    @action(detail=False, url_path="no-leidas")
    def no_leidas(self, request):
        """Contador para la campana. Es la consulta del polling: solo cuenta."""
        return Response({"no_leidas": Notificacion.objects.filter(usuario=request.user, leida=False).count()})

    @extend_schema(request=None, responses=NotificacionSerializer)
    @action(detail=True, methods=["post"])
    def leer(self, request, pk=None):
        notificacion = self.get_object()
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.leida_at = timezone.now()
            notificacion.save(update_fields=["leida", "leida_at"])
        return Response(self.get_serializer(notificacion).data)

    @extend_schema(request=None, responses=CONTADOR)
    @action(detail=False, methods=["post"], url_path="leer-todas")
    def leer_todas(self, request):
        Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True, leida_at=timezone.now())
        return Response({"no_leidas": 0})


@extend_schema(tags=["notificaciones"])
class EnvioMasivoViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Envíos masivos (RF-076). Los roles locales solo envían y ven los de su entidad."""

    serializer_class = EnvioMasivoSerializer
    permission_classes = [PermisoModulo]
    modulo = "notificaciones"
    acciones_permiso = {"contar": CREAR}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return EnvioMasivo.objects.none()
        return filtrar_por_entidad(EnvioMasivo.objects.select_related("enviado_por"), self.request.user)

    def create(self, request, *args, **kwargs):
        datos = self.get_serializer(data=request.data)
        datos.is_valid(raise_exception=True)
        envio = services.enviar_masivo(
            request.user,
            datos.validated_data["grupo"],
            datos.validated_data["asunto"],
            datos.validated_data["cuerpo"],
            datos.validated_data.get("por_correo", False),
        )
        return Response(self.get_serializer(envio).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=GrupoSerializer, responses=inline_serializer("ConteoGrupo", {
        "destinatarios": serializers.IntegerField(), "descripcion": serializers.CharField(),
    }))
    @action(detail=False, methods=["post"])
    def contar(self, request):
        """Cuántos destinatarios tiene un grupo, antes de enviar."""
        grupo = GrupoSerializer(data=request.data)
        grupo.is_valid(raise_exception=True)
        usuarios, descripcion, _, _ = services.resolver_grupo(grupo.validated_data, request.user)
        return Response({"destinatarios": usuarios.count(), "descripcion": descripcion})
