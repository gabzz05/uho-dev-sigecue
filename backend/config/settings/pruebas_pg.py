"""Pruebas contra PostgreSQL (el motor de producción) en vez de SQLite.

SQLite ignora `select_for_update`, así que hay errores que solo aparecen con
PostgreSQL. Se ejecuta dentro del contenedor del backend (ver DESARROLLO.md).
"""

import os

from config.settings.dev import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# El contenedor trae los valores de producción; las pruebas esperan los de desarrollo.
CELERY_TASK_ALWAYS_EAGER = True
FRONTEND_URL = "http://localhost:5173"
