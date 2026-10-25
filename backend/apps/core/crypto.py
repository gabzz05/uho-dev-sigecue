"""Cifrado de datos personales en reposo (RG-025).

- `cifrar` / `descifrar`: AES-256-GCM con nonce aleatorio. El mismo valor
  produce textos cifrados distintos cada vez, por lo que no se puede buscar
  ni exigir unicidad sobre la columna cifrada.
- `hash_busqueda`: HMAC-SHA256 determinista del valor normalizado. Se guarda
  en una columna aparte para comprobar unicidad y buscar por igualdad
  (p. ej. buscar un CI en el listado público) sin descifrar nada.

Las claves vienen de la configuración (`FIELD_ENCRYPTION_KEY` y
`SEARCH_HASH_KEY`, ambas de 32 bytes en base64). Si se pierde
`FIELD_ENCRYPTION_KEY`, los datos cifrados son irrecuperables.
"""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

_PREFIJO = "v1:"
_NONCE_BYTES = 12


def _clave(nombre: str) -> bytes:
    clave = base64.b64decode(getattr(settings, nombre))
    if len(clave) != 32:
        raise ValueError(f"{nombre} debe ser de 32 bytes codificados en base64.")
    return clave


def cifrar(valor: str) -> str:
    nonce = os.urandom(_NONCE_BYTES)
    cifrado = AESGCM(_clave("FIELD_ENCRYPTION_KEY")).encrypt(nonce, valor.encode("utf-8"), None)
    return _PREFIJO + base64.b64encode(nonce + cifrado).decode("ascii")


def descifrar(token: str) -> str:
    if not token.startswith(_PREFIJO):
        raise ValueError("Formato de valor cifrado desconocido.")
    crudo = base64.b64decode(token[len(_PREFIJO):])
    nonce, cifrado = crudo[:_NONCE_BYTES], crudo[_NONCE_BYTES:]
    return AESGCM(_clave("FIELD_ENCRYPTION_KEY")).decrypt(nonce, cifrado, None).decode("utf-8")


def normalizar(valor: str) -> str:
    return "".join(valor.split()).lower()


def hash_busqueda(valor: str) -> str:
    return hmac.new(
        _clave("SEARCH_HASH_KEY"), normalizar(valor).encode("utf-8"), hashlib.sha256
    ).hexdigest()


def generar_clave() -> str:
    """Genera una clave nueva para `.env`."""
    return base64.b64encode(os.urandom(32)).decode("ascii")
