from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.ambito import filtrar_por_entidad
from apps.core.exceptions import ErrorDeNegocio
from apps.roles.catalogo import EDITAR, VER
from apps.roles.models import Rol
from apps.roles.permissions import PermisoModulo
from apps.roles.serializers import RolSerializer
from apps.users.models import Usuario
from apps.users.serializers import UsuarioAdminSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("rol", str, description="Código del rol"),
            OpenApiParameter("activo", bool),
            OpenApiParameter("buscar", str, description="Usuario, nombre o apellidos"),
        ]
    )
)
class UsuarioViewSet(viewsets.ModelViewSet):
    """Usuarios internos (RF-014 a RF-017). Los aspirantes no se gestionan aquí.

    Los usuarios no se borran, para conservar la trazabilidad: se desactivan
    con `bloquear` y se reactivan con `desbloquear`.
    """

    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    serializer_class = UsuarioAdminSerializer
    permission_classes = [PermisoModulo]
    modulo = "usuarios"
    acciones_permiso = {"bloquear": EDITAR, "desbloquear": EDITAR, "roles_asignables": VER}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # Generación del esquema OpenAPI.
            return Usuario.objects.none()
        # Los roles locales solo ven a los usuarios de su entidad (RG-027).
        qs = filtrar_por_entidad(
            Usuario.objects.select_related("rol", "facultad", "cum_fum", "area", "cargo")
            .exclude(rol__codigo=Rol.ASPIRANTE)
            .order_by("username"),
            self.request.user,
        )
        params = self.request.query_params
        if rol := params.get("rol"):
            qs = qs.filter(rol__codigo=rol)
        if (activo := params.get("activo")) in ("true", "false"):
            qs = qs.filter(is_active=activo == "true")
        if buscar := params.get("buscar"):
            qs = qs.filter(
                Q(username__icontains=buscar) | Q(first_name__icontains=buscar) | Q(last_name__icontains=buscar)
            )
        return qs

    def _exigir_gestionable(self, usuario):
        if usuario == self.request.user:
            raise ErrorDeNegocio("No puedes realizar esta acción sobre tu propia cuenta.")
        if usuario.rol_id and usuario.rol.es_global and not self.request.user.es_superadmin:
            raise ErrorDeNegocio("Solo el Superadmin gestiona usuarios con roles globales.")

    @extend_schema(responses=RolSerializer(many=True))
    @action(detail=False, url_path="roles-asignables", pagination_class=None)
    def roles_asignables(self, request):
        """Roles que el usuario actual puede asignar. No exige `roles.ver`.

        - Superadmin: todos menos aspirante.
        - Otros: solo roles locales; los roles locales, solo los de su mismo ámbito.
        """
        qs = Rol.objects.filter(activo=True).exclude(codigo=Rol.ASPIRANTE).prefetch_related("permisos")
        actor = request.user
        if not actor.es_superadmin:
            qs = qs.filter(ambito__in=[Rol.Ambito.FACULTAD, Rol.Ambito.CUM_FUM])
            if actor.rol_id and actor.rol.es_local:
                qs = qs.filter(ambito=actor.rol.ambito)
        return Response(RolSerializer(qs.order_by("nombre"), many=True).data)

    @extend_schema(request=None, responses=UsuarioAdminSerializer)
    @action(detail=True, methods=["post"])
    def bloquear(self, request, pk=None):
        """Desactiva la cuenta: no podrá iniciar sesión (RF-017)."""
        usuario = self.get_object()
        self._exigir_gestionable(usuario)
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        return Response(self.get_serializer(usuario).data)

    @extend_schema(request=None, responses=UsuarioAdminSerializer)
    @action(detail=True, methods=["post"])
    def desbloquear(self, request, pk=None):
        """Reactiva la cuenta y levanta el bloqueo temporal por intentos fallidos."""
        usuario = self.get_object()
        self._exigir_gestionable(usuario)
        usuario.is_active = True
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["is_active", "intentos_fallidos", "bloqueado_hasta"])
        return Response(self.get_serializer(usuario).data, status=status.HTTP_200_OK)
