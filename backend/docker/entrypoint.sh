#!/bin/sh
# Arranque del contenedor del backend.
#
# - `claves`: imprime claves nuevas para el .env (no necesita base de datos).
# - `gunicorn ...` (por defecto): comprueba la configuración, espera a
#   PostgreSQL, migra, recoge los estáticos, crea el Superadmin si se pidió y
#   arranca el servidor.
# - Cualquier otro comando (celery, manage.py...) se ejecuta tal cual.
set -e

if [ "$1" = "claves" ]; then
    python - <<'EOF'
import base64, secrets
print("DJANGO_SECRET_KEY=" + secrets.token_urlsafe(64))
print("FIELD_ENCRYPTION_KEY=" + base64.b64encode(secrets.token_bytes(32)).decode())
print("SEARCH_HASH_KEY=" + base64.b64encode(secrets.token_bytes(32)).decode())
EOF
    exit 0
fi

for variable in DJANGO_SECRET_KEY FIELD_ENCRYPTION_KEY SEARCH_HASH_KEY POSTGRES_PASSWORD; do
    eval valor="\${$variable:-}"
    if [ -z "$valor" ]; then
        echo "ERROR: falta $variable en .env. Genera las claves con:" >&2
        echo "  docker compose run --rm --no-deps backend claves" >&2
        exit 1
    fi
done

echo "Esperando a PostgreSQL en ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'EOF'
import os, time
import psycopg

for intento in range(60):
    try:
        psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "db"), port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
        ).close()
        break
    except psycopg.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL no responde.")
EOF

if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --verbosity 0
    if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
        # Solo la primera vez: si el usuario ya existe no se toca.
        python manage.py shell -c "import os, sys; from apps.users.models import Usuario; sys.exit(0 if Usuario.objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).exists() else 1)" \
            || python manage.py createsuperuser --noinput
    fi
fi

exec "$@"
