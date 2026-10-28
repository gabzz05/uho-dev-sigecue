"""Configuración de producción: PostgreSQL y endurecimiento HTTPS."""

from config.env import env_int, env_str

from .base import *  # noqa: F401,F403

SECRET_KEY = env_str("DJANGO_SECRET_KEY")

# RG-025: claves de cifrado de datos personales y de hash de búsqueda.
FIELD_ENCRYPTION_KEY = env_str("FIELD_ENCRYPTION_KEY")
SEARCH_HASH_KEY = env_str("SEARCH_HASH_KEY")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB"),
        "USER": env_str("POSTGRES_USER"),
        "PASSWORD": env_str("POSTGRES_PASSWORD"),
        "HOST": env_str("POSTGRES_HOST", "localhost"),
        "PORT": env_int("POSTGRES_PORT", 5432),
        "CONN_MAX_AGE": 60,
    }
}

# RG-006: todo el tráfico por HTTPS (el TLS lo termina el proxy inverso).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
AUDITORIA_CONFIAR_X_FORWARDED_FOR = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Límites de peticiones (login, registro, interés, resultados):
# - la cuenta se lleva en Redis, compartida por todos los procesos de gunicorn;
#   con la caché en memoria cada proceso contaba por su lado;
# - la IP del cliente es la que añade nginx al final de X-Forwarded-For; sin
#   NUM_PROXIES todas las peticiones parecían venir de nginx y el límite se
#   aplicaba a todo el sitio a la vez.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env_str("CACHE_URL", "redis://localhost:6379/1"),
    }
}
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": env_int("NUM_PROXIES", 1)}
