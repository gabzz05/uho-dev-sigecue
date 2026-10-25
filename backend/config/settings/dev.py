"""Configuración de desarrollo y pruebas: SQLite y depuración activa."""

from config.env import env_bool, env_str

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "dev-insecure-solo-para-desarrollo")

# Claves fijas SOLO para desarrollo y pruebas (32 bytes en base64).
FIELD_ENCRYPTION_KEY = env_str("FIELD_ENCRYPTION_KEY", "ZGV2LWNsYXZlLWNpZnJhZG8tMzItYnl0ZXMtLS0tLS0=")
SEARCH_HASH_KEY = env_str("SEARCH_HASH_KEY", "ZGV2LWNsYXZlLWhhc2gtYnVzcXVlZGEtMzJieXRlcyE=")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Sin Redis local, las tareas de Celery se ejecutan en el mismo proceso.
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_TASK_EAGER_PROPAGATES = True

# Los correos se imprimen en la consola del runserver.
EMAIL_BACKEND = env_str("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# En http://localhost la cookie no puede ser Secure.
AUTH_REFRESH_COOKIE = {**AUTH_REFRESH_COOKIE, "secure": False}  # noqa: F405
