from django.db import models

from . import crypto


class CampoCifrado(models.TextField):
    """Texto cifrado en la base de datos y en claro en Python.

    No admite búsquedas ni restricciones de unicidad: para eso se usa una
    columna de `hash_busqueda` al lado (ver `apps.core.crypto`).
    """

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return crypto.descifrar(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return crypto.cifrar(value)
