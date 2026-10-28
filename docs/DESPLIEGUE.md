# Despliegue en producción

Guía para instalar SIGECUE en un servidor sin Docker, en Linux, macOS o
Windows. Para la versión con contenedores ver [DOCKER.md](DOCKER.md).

## Qué se instala

| Componente | Función |
|---|---|
| Python 3.12+ | Ejecuta el backend (Django) |
| Node.js 20+ | Solo para compilar el frontend; no se usa en tiempo de ejecución |
| PostgreSQL 14+ | Base de datos |
| Redis 6+ | Cola de tareas de Celery |
| gunicorn | Servidor de la aplicación Django |
| Celery (worker + beat) | Tareas programadas |
| nginx | Sirve el frontend, hace de proxy hacia la API y termina el HTTPS |

El orden es siempre el mismo:

1. Instalar los paquetes del sistema operativo.
2. Seguir los pasos comunes.
3. Dejar los servicios corriendo según el sistema operativo.

---

## 1. Paquetes del sistema operativo

### Linux — Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential \
    postgresql redis-server nginx git
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Linux — RHEL / Rocky / AlmaLinux / Fedora

```bash
sudo dnf install -y python3 python3-devel gcc postgresql-server redis nginx git nodejs
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql redis
```

### macOS (Homebrew)

```bash
brew install python@3.13 node@20 postgresql@16 redis nginx git
brew services start postgresql@16
brew services start redis
```

### Windows

gunicorn y el worker de Celery **no funcionan de forma nativa en Windows**.
La vía recomendada es usar **WSL2**: un Ubuntu completo dentro de Windows.

1. En PowerShell como administrador:
   ```powershell
   wsl --install -d Ubuntu
   ```
   Reiniciar si lo pide y crear el usuario de Ubuntu.
2. Activar systemd en WSL. Dentro de Ubuntu, crear `/etc/wsl.conf` con:
   ```ini
   [boot]
   systemd=true
   ```
   Después, en PowerShell: `wsl --shutdown`, y volver a abrir Ubuntu.
3. Dentro de Ubuntu, seguir **toda** la guía como en **Linux — Debian / Ubuntu**.
4. Para que el sistema sea accesible desde la red, WSL2 debe redirigir los
   puertos 80/443 de Windows. En Windows 11 lo más simple es el modo de red
   espejo. En `%UserProfile%\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   Abrir además los puertos en el Firewall de Windows:
   ```powershell
   New-NetFirewallRule -DisplayName "SIGECUE HTTP/HTTPS" -Direction Inbound -Protocol TCP -LocalPort 80,443 -Action Allow
   ```
5. Para que WSL arranque con el servidor, crear en el Programador de tareas
   una tarea "Al iniciar el sistema" que ejecute `wsl -d Ubuntu --exec /bin/true`.

> Una instalación 100 % nativa en Windows requiere reemplazar gunicorn por un
> servidor compatible y usar Redis para Windows (Memurai). No está
> contemplada en el stack actual.

### Librerías de WeasyPrint (PDF)

La exportación a PDF (WeasyPrint) necesita Pango y sus dependencias. Sin ellas
el sistema funciona, pero los PDF responden con un error.

| Sistema | Instalación |
|---|---|
| Debian / Ubuntu / WSL | `sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-dejavu-core` |
| RHEL / Rocky / Fedora | `sudo dnf install -y pango harfbuzz dejavu-sans-fonts` |
| macOS | `brew install pango` |
| Windows nativo (desarrollo) | Instalar [MSYS2](https://www.msys2.org/) y, en su terminal, `pacman -S mingw-w64-ucrt-x86_64-pango`. Después añadir `C:\msys64\ucrt64\bin` al `PATH` de Windows y abrir una terminal nueva. |

Comprobación (en Windows, `.venv\Scripts\python`):

```bash
.venv/bin/python -c "from weasyprint import HTML; HTML(string='ok').write_pdf()"
```

Si no da error, los PDF funcionan.

---

## 2. Pasos comunes

Los comandos usan sintaxis de Linux/macOS. En Windows se ejecutan dentro de
WSL. Las rutas de ejemplo son `/opt/sigecue` para el código y
`/var/lib/sigecue/media` para los archivos subidos. En macOS se puede usar
`/usr/local/sigecue` y `/usr/local/var/sigecue/media`.

### 2.1 Base de datos PostgreSQL

```bash
sudo -u postgres psql      # en macOS: psql postgres
```
```sql
CREATE USER sigecue WITH PASSWORD 'una-contraseña-segura';
CREATE DATABASE sigecue OWNER sigecue ENCODING 'UTF8';
\q
```

### 2.2 Código y usuario del servicio

Linux / WSL:

```bash
sudo useradd --system --create-home --home-dir /opt/sigecue sigecue
sudo -u sigecue git clone https://github.com/gabzz05/uho-dev-sigecue.git /opt/sigecue/app
sudo mkdir -p /var/lib/sigecue/media /var/lib/sigecue/media_publica
sudo chown sigecue:sigecue /var/lib/sigecue/media /var/lib/sigecue/media_publica
```

En macOS se puede clonar con el usuario administrador del equipo, sin crear un
usuario de sistema.

La carpeta de archivos subidos queda **fuera** del directorio público de nginx
a propósito (RG-012). Los archivos solo se entregan a través de la API, que
comprueba permisos.

### 2.3 Backend

```bash
cd /opt/sigecue/app/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements/prod.txt
cp .env.example .env
nano .env
```

(En Linux, anteponer `sudo -u sigecue` a cada comando para que los archivos
pertenezcan al usuario del servicio.)

#### Variables de entorno (`backend/.env`)

El archivo se lee con `python-dotenv`. Las variables definidas en el sistema
tienen prioridad sobre las del archivo.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DJANGO_SECRET_KEY` | Sí | Clave larga y aleatoria. Generar con `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | Sí | Dominios separados por coma, p. ej. `sigecue.uho.edu.cu` |
| `FIELD_ENCRYPTION_KEY` | Sí | Clave AES-256 para cifrar CI, celular y email (RG-025). Generar con `python manage.py generar_clave`. **Guardarla en lugar seguro: si se pierde, esos datos no se pueden recuperar.** |
| `SEARCH_HASH_KEY` | Sí | Clave del hash que permite buscar y comprobar unicidad del CI sin descifrarlo. Generar igual que la anterior (debe ser distinta). No se puede cambiar una vez haya datos. |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Sí | Datos de la base creada en 2.1 |
| `POSTGRES_HOST` / `POSTGRES_PORT` | No | Por defecto `localhost` / `5432` |
| `MEDIA_ROOT` | No | Carpeta privada de archivos subidos por los aspirantes (creada en 2.2) |
| `PUBLIC_MEDIA_ROOT` | No | Carpeta de imágenes públicas (carreras, facultades, CUM/FUM). Recomendado `/var/lib/sigecue/media_publica`. Debe coincidir con el `alias` de `/media/` en nginx. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | No | Por defecto `redis://localhost:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | No | Debe ser `False` en producción |
| `API_PAGE_SIZE` | No | Elementos por página en la API (20) |
| `FRONTEND_URL` | Sí | URL pública del sistema, p. ej. `https://sigecue.uho.edu.cu`. Se usa en los enlaces de los correos. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | Sí | SMTP corporativo. También se puede configurar en el panel (Configuración → Correo); si se activa allí, tiene prioridad sobre estas variables. |
| `DEFAULT_FROM_EMAIL` | No | Remitente de los correos |
| `LOGIN_MAX_INTENTOS` / `LOGIN_BLOQUEO_MINUTOS` | No | Valores iniciales del bloqueo temporal (5 / 15). Después se cambian en el panel (Configuración → Parámetros). |
| `AUTH_THROTTLE_RATE` | No | Límite de peticiones a login y registro por IP (`20/min`) |
| `INTERES_THROTTLE_RATE` | No | Límite de expresiones de interés por IP en la landing (`10/hour`) |
| `RESULTADOS_THROTTLE_RATE` | No | Límite de consultas de resultado por CI y por IP en la landing (`10/hour`) |
| `AUTH_COOKIE_SECURE` | No | `True` (la cookie de sesión solo viaja por HTTPS). No cambiar en producción. |
| `SGU_PROVEEDOR` | No | Integración con auth.uho.edu.cu. Ver [SGU.md](SGU.md). |

Tras la primera migración, crear el Superadmin:

```bash
.venv/bin/python manage.py createsuperuser
```

Inicializar la base de datos y los archivos estáticos:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

`DJANGO_SETTINGS_MODULE=config.settings.prod` es imprescindible. Sin esa
variable, `manage.py` usa la configuración de desarrollo (SQLite).

### 2.4 Frontend

```bash
cd /opt/sigecue/app/frontend
npm ci
npm run build    # genera frontend/dist/
```

### 2.5 nginx

Crear la configuración del sitio:

| Sistema | Ruta del archivo |
|---|---|
| Debian / Ubuntu / WSL | `/etc/nginx/sites-available/sigecue`, enlazado en `sites-enabled/` |
| RHEL / Rocky / Fedora | `/etc/nginx/conf.d/sigecue.conf` |
| macOS (Homebrew) | `$(brew --prefix)/etc/nginx/servers/sigecue.conf` |

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

    # Imágenes públicas (carreras, facultades, CUM/FUM). Los archivos de los
    # aspirantes (MEDIA_ROOT) NO se publican aquí: solo los entrega la API.
    location /media/ { alias /var/lib/sigecue/media_publica/; }

    # /admin es el panel de React: no se envía a Django.
    location ~ ^/(api|django-admin)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA: cualquier otra ruta la resuelve React
    location / { try_files $uri /index.html; }
}
```

Debian / Ubuntu / WSL:

```bash
sudo ln -s /etc/nginx/sites-available/sigecue /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

En RHEL y Fedora: `sudo nginx -t && sudo systemctl reload nginx`.
Si SELinux está activo, permitir el proxy con
`sudo setsebool -P httpd_can_network_connect 1`.

En macOS: `nginx -t && brew services restart nginx`.

---

## 3. Servicios

Son tres procesos que deben estar siempre corriendo:

| Servicio | Comando (desde `backend/`) |
|---|---|
| Web | `.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 4` |
| Worker | `.venv/bin/celery -A config worker -l info` |
| Beat | `.venv/bin/celery -A config beat -l info` |

Los tres necesitan `DJANGO_SETTINGS_MODULE=config.settings.prod`.

### Linux y Windows (WSL): systemd

`/etc/systemd/system/sigecue-web.service`:

```ini
[Unit]
Description=SIGECUE (gunicorn)
After=network.target postgresql.service redis.service

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

`sigecue-worker.service` y `sigecue-beat.service` se crean copiando el
anterior y cambiando `Description` y `ExecStart` por el comando
correspondiente de la tabla.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sigecue-web sigecue-worker sigecue-beat
sudo systemctl status sigecue-web    # comprobar
```

En RHEL y Fedora el servicio de Redis se llama `redis`, igual que en Debian.

### macOS: launchd

Un archivo por servicio en `~/Library/LaunchAgents/`, por ejemplo
`cu.edu.uho.sigecue.web.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>cu.edu.uho.sigecue.web</string>
  <key>WorkingDirectory</key><string>/usr/local/sigecue/app/backend</string>
  <key>EnvironmentVariables</key>
  <dict><key>DJANGO_SETTINGS_MODULE</key><string>config.settings.prod</string></dict>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/sigecue/app/backend/.venv/bin/gunicorn</string>
    <string>config.wsgi:application</string>
    <string>--bind</string><string>127.0.0.1:8000</string>
    <string>--workers</string><string>4</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

Repetir para `worker` y `beat` cambiando `Label` y `ProgramArguments`.
Activar cada uno:

```bash
launchctl load ~/Library/LaunchAgents/cu.edu.uho.sigecue.web.plist
```

---

## 4. Actualizar a una nueva versión

```bash
cd /opt/sigecue/app
git pull
cd backend
.venv/bin/pip install -r requirements/prod.txt
export DJANGO_SETTINGS_MODULE=config.settings.prod
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
cd ../frontend && npm ci && npm run build
```

Reiniciar los servicios:

| Sistema | Comando |
|---|---|
| Linux / WSL | `sudo systemctl restart sigecue-web sigecue-worker sigecue-beat` |
| macOS | `launchctl kickstart -k gui/$(id -u)/cu.edu.uho.sigecue.web` (y lo mismo con worker y beat) |

---

## 5. Copias de seguridad (RG-013, RNF-004)

Copia diaria de PostgreSQL con retención de 30 días. Incluir también la
carpeta de archivos subidos (`MEDIA_ROOT`).

Linux / WSL — `/etc/cron.d/sigecue-backup`:

```cron
0 2 * * * postgres pg_dump -Fc sigecue > /var/backups/sigecue/sigecue-$(date +\%F).dump && find /var/backups/sigecue -name '*.dump' -mtime +30 -delete
```

En macOS se puede usar la misma línea con `crontab -e`, quitando la columna
`postgres` (usuario).

En Windows con WSL, la línea de cron funciona dentro de Ubuntu siempre que WSL
esté corriendo (ver el paso 5 de la sección de Windows). Conviene además copiar
`/var/backups/sigecue` fuera de WSL, p. ej. a `/mnt/c/Backups/sigecue`.

**Copias de seguridad y retención de datos (RG-028).** La anonimización no es
retroactiva sobre las copias ya generadas. Con la retención de 30 días, los
datos anonimizados desaparecen de las copias en el ciclo natural siguiente. No
amplíes esa retención sin revisar la política de datos personales, y si
restauras una copia antigua, vuelve a ejecutar la retención (Configuración →
Retención de datos) antes de reabrir el sistema.

## 6. Lista de comprobación para la primera puesta en producción

**Antes de abrir el sistema:**

- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod` en el servicio web, el worker y beat.
- [ ] `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY` y `SEARCH_HASH_KEY` generadas
  y **guardadas fuera del servidor**. Sin la clave de cifrado no se recuperan
  CI, correo ni celular.
- [ ] `DJANGO_ALLOWED_HOSTS` y `FRONTEND_URL` con el dominio real;
  `AUTH_COOKIE_SECURE=True`; `CELERY_TASK_ALWAYS_EAGER=False`.
- [ ] `migrate`, `collectstatic` y `check --deploy` sin errores (§2.3).
- [ ] Superadmin creado (`createsuperuser`).
- [ ] HTTPS activo en nginx con TLS 1.2 o superior (RG-006). `/media/` solo
  sirve `PUBLIC_MEDIA_ROOT`; `MEDIA_ROOT` **no** se publica.
- [ ] Servicios web, worker y beat activos y arrancando solos (§3).
- [ ] Librerías de WeasyPrint instaladas: exportar un PDF de prueba desde el
  panel.
- [ ] RNF-006: fijar `build: { target: ['chrome90', 'firefox88', 'edge90', 'safari14'] }`
  en `frontend/vite.config.js`, recompilar y probar en esos navegadores.
- [ ] Copia diaria de la base de datos y de `MEDIA_ROOT`, con 30 días de
  retención (§5). Hacer **una restauración de prueba** (RNF-004: RTO ≤ 4 h).

**En el panel, como Superadmin:**

- [ ] Configuración → Correo: SMTP corporativo y envío de prueba.
- [ ] Configuración → Identidad visual: nombre, colores y escudo.
- [ ] Configuración → Parámetros: máximo de carreras, intentos de acceso y
  plazos de retención.
- [ ] Revisar las plantillas de correo, los documentos del aspirante y los
  campos de prematrícula.
- [ ] Nomencladores: Facultades, CUM/FUM, carreras, áreas, departamentos y
  cargos (los municipios ya vienen cargados).
- [ ] Usuarios internos de cada entidad, con su rol; revisar la matriz de
  permisos.
- [ ] Sustituir los textos provisionales: política de privacidad y sección
  institucional ([ANOTACIONES.md](ANOTACIONES.md)).

**Después:** revisar Logs de auditoría y el log de aplicación
(`backend/logs/`) durante los primeros días.

