"""Lectura de variables de entorno.

Carga `backend/.env` (si existe) en `os.environ` sin sobrescribir variables
ya definidas en el sistema, y expone helpers tipados para leerlas.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path = BASE_DIR / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def env_str(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {key}")
    return value


def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(key, default).split(",") if item.strip()]
