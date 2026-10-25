from django.core.validators import RegexValidator
from rest_framework import serializers

from apps.core import crypto
from apps.users.models import Usuario

validar_ci = RegexValidator(r"^\d{11}$", "El carnet de identidad debe tener 11 dígitos, sin espacios ni guiones.")
validar_celular = RegexValidator(r"^5\d{7}$", "El celular debe tener 8 dígitos y empezar por 5.")


def validar_unico(campo_hash, valor, mensaje, excluir=None):
    qs = Usuario.objects.filter(**{campo_hash: crypto.hash_busqueda(valor)})
    if excluir is not None:
        qs = qs.exclude(pk=excluir.pk)
    if qs.exists():
        raise serializers.ValidationError(mensaje)
    return valor
