from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.core.ambito import es_de_su_entidad
from apps.core.validators import FORMATOS_FOTO_ASPIRANTE, validar_imagen
from apps.roles.models import Rol

from .models import Usuario
from .validators import validar_celular, validar_ci, validar_unico

CI_REGISTRADO = "Ya existe una cuenta con este carnet de identidad."
EMAIL_REGISTRADO = "Ya existe una cuenta con este correo electrónico."


class LoginSerializer(serializers.Serializer):
    identificador = serializers.CharField(help_text="Email (aspirantes) o nombre de usuario (internos).")
    password = serializers.CharField(trim_whitespace=False)


class RegistroSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150)
    ci = serializers.CharField(validators=[validar_ci])
    email = serializers.EmailField()
    celular = serializers.CharField(validators=[validar_celular])
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    acepta_privacidad = serializers.BooleanField(help_text="Consentimiento explícito de la política de privacidad (RG-026).")

    def validate_ci(self, ci):
        return validar_unico("ci_hash", ci, CI_REGISTRADO)

    def validate_email(self, email):
        return validar_unico("email_hash", email.lower(), EMAIL_REGISTRADO)

    def validate_acepta_privacidad(self, acepta):
        if not acepta:
            raise serializers.ValidationError("Debes aceptar la política de privacidad para registrarte.")
        return acepta

    def validate(self, attrs):
        usuario = Usuario(first_name=attrs["nombre"], last_name=attrs["apellidos"], email=attrs["email"])
        try:
            validate_password(attrs["password"], usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class ActivacionSerializer(serializers.Serializer):
    token = serializers.CharField()


class RolResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["codigo", "nombre", "ambito"]


def resumen_entidad(usuario):
    if usuario.facultad_id:
        return {"tipo": "facultad", "id": usuario.facultad_id, "nombre": usuario.facultad.nombre}
    if usuario.cum_fum_id:
        return {"tipo": "cum_fum", "id": usuario.cum_fum_id, "nombre": usuario.cum_fum.nombre}
    return None


ENTIDAD_SCHEMA = inline_serializer(
    "EntidadResumen",
    {"tipo": serializers.ChoiceField(["facultad", "cum_fum"]), "id": serializers.IntegerField(), "nombre": serializers.CharField()},
    allow_null=True,
)


class UsuarioActualSerializer(serializers.ModelSerializer):
    """Perfil del usuario autenticado (RF-018). Solo celular y foto son editables."""

    nombre = serializers.CharField(source="first_name", read_only=True)
    apellidos = serializers.CharField(source="last_name", read_only=True)
    rol = RolResumenSerializer(read_only=True)
    entidad = serializers.SerializerMethodField()
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default=None)
    permisos = serializers.SerializerMethodField()
    celular = serializers.CharField(validators=[validar_celular], required=False)
    foto = serializers.ImageField(required=False, allow_null=True, validators=[validar_imagen])

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "nombre", "apellidos", "email", "ci", "celular", "foto",
            "origen", "rol", "entidad", "area_nombre", "es_superadmin", "permisos",
        ]
        read_only_fields = ["username", "email", "ci", "origen", "es_superadmin"]

    @extend_schema_field(ENTIDAD_SCHEMA)
    def get_entidad(self, usuario):
        return resumen_entidad(usuario)

    def get_permisos(self, usuario) -> list[str]:
        """Códigos `modulo.accion`. El superadmin recibe `["*"]`."""
        return ["*"] if usuario.es_superadmin else sorted(usuario.codigos_permiso)

    def validate_foto(self, foto):
        usuario = self.instance
        if usuario is not None and usuario.es_aspirante:
            from apps.aspirantes import services as aspirantes

            # RF-046: la foto del aspirante es JPG o PNG y cuenta en su cuota (RNF-005).
            if foto is not None:
                validar_imagen(foto, FORMATOS_FOTO_ASPIRANTE)
            aspirantes.validar_foto(usuario, foto)
        return foto

    def to_representation(self, usuario):
        datos = super().to_representation(usuario)
        # La foto está en el almacenamiento privado: se pide a la API con el token.
        # El parámetro `v` cambia con cada foto nueva para no reutilizar la caché.
        datos["foto"] = f"/auth/me/foto/?v={usuario.foto.name.rsplit('/', 1)[-1]}" if usuario.foto else None
        return datos


class RecuperarPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class RestablecerPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        from apps.users.services import recuperacion

        usuario = recuperacion.usuario_del_enlace(attrs["uid"], attrs["token"])
        try:
            validate_password(attrs["password"], usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs | {"usuario": usuario}


class CambiarPasswordSerializer(serializers.Serializer):
    actual = serializers.CharField(trim_whitespace=False)
    nueva = serializers.CharField(trim_whitespace=False)

    def validate_actual(self, actual):
        if not self.context["request"].user.check_password(actual):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return actual

    def validate_nueva(self, nueva):
        try:
            validate_password(nueva, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return nueva


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """Gestión de usuarios internos (RF-014 a RF-016).

    Reglas de entidad:
    - Rol global: sin Facultad, CUM/FUM ni área.
    - Rol local: exactamente la entidad de su ámbito (Facultad o CUM/FUM).
    - Rol con `requiere_area` (Jefe de Área): un área de esa misma entidad.
    - Un usuario local solo crea usuarios de su entidad; si no la indica, se usa la suya.
    """

    rol = serializers.SlugRelatedField(slug_field="codigo", queryset=Rol.objects.exclude(codigo=Rol.ASPIRANTE))
    email = serializers.EmailField()
    ci = serializers.CharField(validators=[validar_ci], required=False, allow_blank=True)
    celular = serializers.CharField(validators=[validar_celular], required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    entidad = serializers.SerializerMethodField()
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default=None)
    cargo_nombre = serializers.CharField(source="cargo.nombre", read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "first_name", "last_name", "email", "ci", "celular", "rol",
            "facultad", "cum_fum", "entidad", "area", "area_nombre", "cargo", "cargo_nombre",
            "origen", "is_active", "bloqueado_hasta", "last_login", "date_joined", "password",
        ]
        read_only_fields = ["is_active", "bloqueado_hasta", "last_login", "date_joined"]
        # La exclusión Facultad/CUM la valida `_validar_entidad` con un mensaje claro.
        validators = []

    @extend_schema_field(ENTIDAD_SCHEMA)
    def get_entidad(self, usuario):
        return resumen_entidad(usuario)

    def _actual(self, attrs, campo):
        return attrs[campo] if campo in attrs else getattr(self.instance, campo, None)

    def _validar_entidad(self, attrs, actor):
        rol = self._actual(attrs, "rol")
        facultad = self._actual(attrs, "facultad")
        cum_fum = self._actual(attrs, "cum_fum")
        area = self._actual(attrs, "area")

        if rol.es_global:
            facultad = cum_fum = area = None
        else:
            if facultad is None and cum_fum is None and not actor.es_global:
                facultad, cum_fum = actor.facultad, actor.cum_fum
            if rol.ambito == Rol.Ambito.FACULTAD:
                if facultad is None or cum_fum is not None:
                    raise serializers.ValidationError({"facultad": "Este rol requiere una Facultad."})
            elif cum_fum is None or facultad is not None:
                raise serializers.ValidationError({"cum_fum": "Este rol requiere un CUM/FUM."})
            if not es_de_su_entidad(actor, facultad, cum_fum):
                raise serializers.ValidationError({"facultad": "Solo puedes gestionar usuarios de tu propia entidad."})

            if rol.requiere_area:
                if area is None:
                    raise serializers.ValidationError({"area": "Este rol requiere un área."})
                if (area.facultad_id, area.cum_fum_id) != (getattr(facultad, "pk", None), getattr(cum_fum, "pk", None)):
                    raise serializers.ValidationError({"area": "El área debe pertenecer a la entidad del usuario."})
            else:
                area = None

        attrs.update(facultad=facultad, cum_fum=cum_fum, area=area)

    def validate_email(self, email):
        return validar_unico("email_hash", email.lower(), EMAIL_REGISTRADO, excluir=self.instance)

    def validate_ci(self, ci):
        return validar_unico("ci_hash", ci, CI_REGISTRADO, excluir=self.instance) if ci else ci

    def validate(self, attrs):
        actor = self.context["request"].user
        rol = attrs.get("rol")

        # RF-016: los usuarios globales los gestiona solo el Superadmin.
        tocando_global = (rol is not None and rol.es_global) or (
            self.instance is not None and self.instance.rol_id and self.instance.rol.es_global
        )
        if tocando_global and not actor.es_superadmin:
            raise serializers.ValidationError({"rol": "Solo el Superadmin gestiona usuarios con roles globales."})
        if self.instance is None and rol is None:
            raise serializers.ValidationError({"rol": "Indica el rol del usuario."})
        self._validar_entidad(attrs, actor)

        origen = attrs.get("origen", getattr(self.instance, "origen", Usuario.Origen.LOCAL))
        password = attrs.get("password")
        if self.instance is None and origen == Usuario.Origen.LOCAL and not password:
            raise serializers.ValidationError({"password": "Indica una contraseña para el usuario."})
        if password:
            if origen == Usuario.Origen.SGU:
                raise serializers.ValidationError({"password": "Los usuarios del SGU no tienen contraseña local."})
            try:
                validate_password(password, self.instance)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        usuario = Usuario(email_verificado=True, **validated_data)
        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()
        usuario.save()
        return usuario

    def update(self, usuario, validated_data):
        password = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(usuario, campo, valor)
        if password:
            usuario.set_password(password)
        usuario.save()
        return usuario
