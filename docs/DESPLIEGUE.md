# Despliegue en producción (servidor Linux, sin Docker)

Guía para instalar SIGECUE en un servidor Ubuntu/Debian. Para la versión con
contenedores ver [DOCKER.md](DOCKER.md).

## 1. Paquetes del sistema

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential \
    postgresql redis-server nginx git
# Node.js 20+ (solo para compilar el frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. Base de datos PostgreSQL

```bash
sudo -u postgres psql
```
```sql
CREATE USER sigecue WITH PASSWORD 'una-contraseña-segura';
CREATE DATABASE sigecue OWNER sigecue ENCODING 'UTF8';
\q
```

## 3. Código y usuario del servicio

```bash
sudo useradd --system --create-home --home-dir /opt/sigecue sigecue
sudo -u sigecue git clone https://github.com/gabzz05/uho-dev-sigecue.git /opt/sigecue/app
sudo mkdir -p /var/lib/sigecue/media
sudo chown sigecue:sigecue /var/lib/sigecue/media
```

`/var/lib/sigecue/media` guarda los archivos subidos por los aspirantes. Queda
fuera del directorio público de nginx a propósito (RG-012): los archivos solo
se entregan a través de la API, que comprueba permisos.

## 4. Backend

```bash
cd /opt/sigecue/app/backend
sudo -u sigecue python3 -m venv .venv
sudo -u sigecue .venv/bin/pip install -r requirements/prod.txt
sudo -u sigecue cp .env.example .env
sudo -u sigecue nano .env
```

### Variables de entorno (`backend/.env`)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DJANGO_SECRET_KEY` | Sí | Clave larga y aleatoria. Generar con `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | Sí | Dominios separados por coma, p. ej. `sigecue.uho.edu.cu` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Sí | Datos de la base creada en el paso 2 |
| `POSTGRES_HOST` / `POSTGRES_PORT` | No | Por defecto `localhost` / `5432` |
| `MEDIA_ROOT` | No | Carpeta de archivos subidos. Recomendado `/var/lib/sigecue/media` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | No | Por defecto `redis://localhost:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | No | Debe ser `False` en producción |
| `API_PAGE_SIZE` | No | Elementos por página en la API (20) |

Los servicios del paso 6 indican `DJANGO_SETTINGS_MODULE=config.settings.prod`.
Para los comandos manuales hay que exportarla también:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
sudo -u sigecue -E .venv/bin/python manage.py migrate
sudo -u sigecue -E .venv/bin/python manage.py collectstatic --noinput
sudo -u sigecue -E .venv/bin/python manage.py check --deploy
```

## 5. Frontend

```bash
cd /opt/sigecue/app/frontend
sudo -u sigecue npm ci
sudo -u sigecue npm run build    # genera frontend/dist/
```

## 6. Servicios systemd

`/etc/systemd/system/sigecue-web.service`:

```ini
[Unit]
Description=SIGECUE (gunicorn)
After=network.target postgresql.service

[Service]
User=sigecue
WorkingDirectory=/opt/sigecue/app/backend
Environment=DJANGO_SETTINGS_MODULE=config.settings.prod
ExecStart=/opt/sigecue/app/backend/.venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/sigecue-worker.service` (igual que el anterior cambiando):

```ini
Description=SIGECUE (celery worker)
ExecStart=/opt/sigecue/app/backend/.venv/bin/celery -A config worker -l info
```

`/etc/systemd/system/sigecue-beat.service`:

```ini
Description=SIGECUE (celery beat)
ExecStart=/opt/sigecue/app/backend/.venv/bin/celery -A config beat -l info
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sigecue-web sigecue-worker sigecue-beat
```

## 7. nginx

`/etc/nginx/sites-available/sigecue`:

```nginx
server {
    listen 80;
    server_name sigecue.uho.edu.cu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name sigecue.uho.edu.cu;

    # RG-006: TLS 1.2 o superior
    ssl_certificate     /etc/ssl/certs/sigecue.crt;
    ssl_certificate_key /etc/ssl/private/sigecue.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 6M;   # RNF-005: 5 MB por archivo
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    root /opt/sigecue/app/frontend/dist;

    location /static/ { alias /opt/sigecue/app/backend/staticfiles/; }

    location ~ ^/(api|admin)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA: cualquier otra ruta la resuelve React
    location / { try_files $uri /index.html; }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/sigecue /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 8. Actualizar a una nueva versión

```bash
cd /opt/sigecue/app
sudo -u sigecue git pull
cd backend && sudo -u sigecue .venv/bin/pip install -r requirements/prod.txt
export DJANGO_SETTINGS_MODULE=config.settings.prod
sudo -u sigecue -E .venv/bin/python manage.py migrate
sudo -u sigecue -E .venv/bin/python manage.py collectstatic --noinput
cd ../frontend && sudo -u sigecue npm ci && sudo -u sigecue npm run build
sudo systemctl restart sigecue-web sigecue-worker sigecue-beat
```

## 9. Copias de seguridad (RG-013, RNF-004)

Copia diaria de PostgreSQL con retención de 30 días, p. ej. en
`/etc/cron.d/sigecue-backup`:

```cron
0 2 * * * postgres pg_dump -Fc sigecue > /var/backups/sigecue/sigecue-$(date +\%F).dump && find /var/backups/sigecue -name '*.dump' -mtime +30 -delete
```

Incluir también `/var/lib/sigecue/media` en la copia.
