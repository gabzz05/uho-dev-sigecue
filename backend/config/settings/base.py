"""Configuración común a todos los entornos."""

from config.env import BASE_DIR, env_int, env_list, env_str, load_env_file

load_env_file()

DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
]
LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.auditoria",
]

AUTH_USER_MODEL = "users.Usuario"
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.auditoria.middleware.AuditoriaMiddleware",
]

# Solo debe activarse detrás de un proxy inverso de confianza (nginx).
AUDITORIA_CONFIAR_X_FORWARDED_FOR = False

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# RG-007: hash de contraseñas con Argon2/bcrypt se configura en feature/auth-users.

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Havana"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# RG-012: los archivos subidos se guardan fuera del directorio web público
# y se sirven solo a través de endpoints con control de permisos.
MEDIA_ROOT = env_str("MEDIA_ROOT", str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PaginacionEstandar",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 20),
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # RG-017: fechas en ISO 8601.
    "DATETIME_FORMAT": "iso-8601",
}

# RG-016 / RNF-009: documentación OpenAPI en /api/docs.
SPECTACULAR_SETTINGS = {
    "TITLE": "SIGECUE API",
    "DESCRIPTION": "API del Sistema de Gestión de Carreras por Encuentro — Universidad de Holguín.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

# Celery (tareas programadas: cierre de convocatorias, recordatorios, limpieza).
CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env_str("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False

# RNF-008: logs INFO/WARNING/ERROR con rotación diaria y retención de 90 días.
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LOG_DIR / "sigecue.log",
            "when": "midnight",
            "backupCount": 90,
            "encoding": "utf-8",
            "formatter": "default",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}
