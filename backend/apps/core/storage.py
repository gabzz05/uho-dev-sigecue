"""Almacenamientos de archivos.

- `default` (MEDIA_ROOT): privado. Documentos y fotos de los aspirantes; no lo
  sirve el servidor web, solo la API con control de permisos (RG-012).
- `publico` (PUBLIC_MEDIA_ROOT, URL PUBLIC_MEDIA_URL): contenido institucional
  no sensible, como imágenes de carreras, facultades y CUM/FUM. Lo sirve nginx.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.functional import cached_property


class AlmacenamientoPublico(FileSystemStorage):
    """Como FileSystemStorage, pero con PUBLIC_MEDIA_ROOT/URL leídos en diferido
    (y recalculados si cambian, p. ej. en las pruebas)."""

    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.PUBLIC_MEDIA_ROOT)

    @cached_property
    def base_url(self):
        url = self._value_or_setting(self._base_url, settings.PUBLIC_MEDIA_URL)
        return url if url.endswith("/") else f"{url}/"

    def _clear_cached_properties(self, setting, **kwargs):
        super()._clear_cached_properties(setting, **kwargs)
        if setting in ("PUBLIC_MEDIA_ROOT", "PUBLIC_MEDIA_URL"):
            for propiedad in ("base_location", "location", "base_url"):
                self.__dict__.pop(propiedad, None)


def almacenamiento_publico():
    # Callable: las migraciones guardan la referencia, no una ruta concreta.
    return storages["publico"]
