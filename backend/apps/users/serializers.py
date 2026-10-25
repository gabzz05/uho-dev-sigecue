from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.roles.models import Rol

from .models import Usuario
from .validators import validar_celular, validar_ci, validar_imagen, validar_unico

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


class UsuarioActualSerializer(serializers.ModelSerializer):
    """Perfil del usuario autenticado (RF-018). Solo celular y foto son editables."""

    nombre = serializers.CharField(source="first_name", read_only=True)
    apellidos = serializers.CharField(source="last_name", read_only=True)
    rol = RolResumenSerializer(read_only=True)
    permisos = serializers.SerializerMethodField()
    celular = serializers.CharField(validators=[validar_celular], required=False)
    foto = serializers.ImageField(required=False, allow_null=True, validators=[validar_imagen])

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "nombre", "apellidos", "email", "ci", "celular", "foto",
            "origen", "rol", "es_superadmin", "permisos",
        ]
        read_only_fields = ["username", "email", "ci", "origen", "es_superadmin"]

    def get_permisos(self, usuario) -> list[str]:
        """Códigos `modulo.accion`. El superadmin recibe `["*"]`."""
        return ["*"] if usuario.es_superadmin else sorted(usuario.codigos_permiso)


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
    """Gestión de usuarios internos (RF-014/RF-016)."""

    rol = serializers.SlugRelatedField(slug_field="codigo", queryset=Rol.objects.exclude(codigo=Rol.ASPIRANTE))
    email = serializers.EmailField()
    ci = serializers.CharField(validators=[validar_ci], required=False, allow_blank=True)
    celular = serializers.CharField(validators=[validar_celular], required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "first_name", "last_name", "email", "ci", "celular", "rol",
            "origen", "is_active", "bloqueado_hasta", "last_login", "date_joined", "password",
        ]
        read_only_fields = ["is_active", "bloqueado_hasta", "last_login", "date_joined"]

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
