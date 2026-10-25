"""Configuración de desarrollo y pruebas: SQLite y depuración activa."""

from config.env import env_bool, env_str

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "dev-insecure-solo-para-desarrollo")
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
