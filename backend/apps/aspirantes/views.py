from django.db.models import ProtectedError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import exceptions, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria import services as auditoria
from apps.configuracion.views import PermisoConfiguracion
from apps.core.exceptions import ErrorDeNegocio
from apps.core.validators import TIPO_MIME
from apps.roles.catalogo import EDITAR
from apps.users.models import Usuario

from . import services
from .models import DocumentoAspirante, TipoDocumento
from .permissions import EsAspirante
from .serializers import (
    DocumentoSerializer,
    PerfilAspiranteEditarSerializer,
    PerfilAspiranteSerializer,
    SubirDocumentoSerializer,
    TipoDocumentoSerializer,
)

# Motivos automáticos de las descargas auditadas (sin pedirlos al usuario).
MOTIVO_PROPIO = "consulta_documentacion"
MOTIVO_REVISION = "revision_solicitud"


def _perfil_respuesta(usuario, request):
    return Response(PerfilAspiranteSerializer(services.perfil_de(usuario), context={"request": request}).data)


@extend_schema(tags=["aspirante"])
class PerfilAspiranteView(APIView):
    """Perfil del aspirante autenticado (RF-046). La foto se cambia en /auth/me/."""

    permission_classes = [EsAspirante]

    @extend_schema(responses=PerfilAspiranteSerializer)
    def get(self, request):
        return _perfil_respuesta(request.user, request)

    @extend_schema(request=PerfilAspiranteEditarSerializer, responses=PerfilAspiranteSerializer)
    def patch(self, request):
        datos = PerfilAspiranteEditarSerializer(services.perfil_de(request.user), data=request.data, partial=True)
        datos.is_valid(raise_exception=True)
        services.actualizar_datos(request.user, datos.validated_data)
        return _perfil_respuesta(request.user, request)


@extend_schema(tags=["aspirante"])
class SubirDocumentoView(APIView):
    """Sube (o sustituye) un documento del perfil. La versión anterior se conserva como historial."""

    permission_classes = [EsAspirante]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request={"multipart/form-data": SubirDocumentoSerializer}, responses={201: PerfilAspiranteSerializer})
    def post(self, request):
        datos = SubirDocumentoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        services.subir_documento(request.user, datos.validated_data["tipo"], datos.validated_data["archivo"], datos.validated_data["formato"])
        respuesta = _perfil_respuesta(request.user, request)
        respuesta.status_code = status.HTTP_201_CREATED
        return respuesta


def _auditar_descarga(request, aspirante, accion, archivo, **detalle):
    auditoria.registrar(
        request=request,
        accion=accion,
        modulo="aspirantes",
        entidad_afectada="aspirante",
        entidad_id=str(aspirante.pk),
        detalle={"motivo": MOTIVO_PROPIO if request.user.pk == aspirante.pk else MOTIVO_REVISION, "archivo": archivo, **detalle},
    )


@extend_schema(tags=["aspirante"], responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
class ArchivoDocumentoView(APIView):
    """Archivo de un documento del aspirante, servido por la API con control de acceso (RG-012).

    Lo descargan el propio aspirante y el personal con `solicitudes.documentos_descargar`
    de una entidad donde eligió carrera (o global). Las versiones anteriores, solo
    los roles globales. Cada descarga se audita.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        documento = get_object_or_404(DocumentoAspirante.objects.select_related("perfil__usuario", "tipo"), pk=pk)
        aspirante = documento.perfil.usuario
        # 404 y no 403: no revela si el documento existe.
        if not services.puede_ver_documentos(request.user, aspirante):
            raise exceptions.NotFound()
        if not documento.vigente and not services.puede_ver_historial(request.user):
            raise exceptions.NotFound()

        _auditar_descarga(
            request, aspirante, "descargar documento", documento.nombre_original,
            documento_id=documento.pk, tipo=documento.tipo.nombre, version=documento.version,
        )
        nombre = f"{slugify(documento.tipo.nombre)}-v{documento.version}.{documento.archivo.name.rsplit('.', 1)[-1]}"
        return FileResponse(documento.archivo.open("rb"), content_type=TIPO_MIME[documento.formato], filename=nombre)


def _aspirante_visible(request, usuario_id):
    aspirante = get_object_or_404(Usuario.objects.select_related("rol"), pk=usuario_id)
    if not aspirante.es_aspirante or not services.puede_ver_documentos(request.user, aspirante):
        raise exceptions.NotFound()
    return aspirante


@extend_schema(tags=["aspirante"], responses=DocumentoSerializer(many=True))
class DocumentosAspiranteView(APIView):
    """Documentos de un aspirante para el personal: los vigentes y, a los roles globales, todo el historial."""

    permission_classes = [IsAuthenticated]

    def get(self, request, usuario_id):
        aspirante = _aspirante_visible(request, usuario_id)
        documentos = DocumentoAspirante.objects.filter(perfil__usuario=aspirante).select_related("tipo")
        if not services.puede_ver_historial(request.user):
            documentos = documentos.filter(vigente=True)
        return Response(DocumentoSerializer(documentos, many=True).data)


@extend_schema(tags=["aspirante"], responses={(200, "image/*"): OpenApiTypes.BINARY})
class FotoAspiranteView(APIView):
    """Foto de perfil de un aspirante, con las mismas reglas de acceso que sus documentos."""

    permission_classes = [IsAuthenticated]

    def get(self, request, usuario_id):
        aspirante = _aspirante_visible(request, usuario_id)
        if not aspirante.foto:
            raise exceptions.NotFound()
        _auditar_descarga(request, aspirante, "ver foto de aspirante", aspirante.foto.name.rsplit("/", 1)[-1])
        return FileResponse(aspirante.foto.open("rb"))


@extend_schema(tags=["configuracion"])
class TipoDocumentoViewSet(viewsets.ModelViewSet):
    """Documentos que se piden al aspirante en su perfil. Solo el Superadmin los modifica."""

    queryset = TipoDocumento.objects.all()
    serializer_class = TipoDocumentoSerializer
    permission_classes = [PermisoConfiguracion]
    modulo = "configuracion"
    # El módulo configuración solo tiene ver/editar.
    acciones_permiso = {"create": EDITAR, "destroy": EDITAR}
    parser_classes = [JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        if buscar := self.request.query_params.get("buscar"):
            qs = qs.filter(nombre__icontains=buscar)
        return qs

    def perform_destroy(self, tipo):
        try:
            tipo.delete()
        except ProtectedError:
            raise ErrorDeNegocio("Ya hay aspirantes que subieron este documento. Desactívalo en lugar de eliminarlo.")
