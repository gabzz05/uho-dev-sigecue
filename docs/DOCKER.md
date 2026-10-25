# Contenerización con Docker (pendiente)

> Por decisión del cliente, Docker no se implementa todavía. La ERS lo exige
> para la entrega (RG-021, RE-007, criterio de aceptación 15), así que este
> documento describe cómo hacerlo cuando toque.

## Servicios

| Servicio | Imagen base | Función |
|---|---|---|
| `db` | `postgres:16` | Base de datos |
| `redis` | `redis:7` | Broker de Celery |
| `backend` | `python:3.13-slim` | Django servido con gunicorn |
| `worker` | misma imagen que `backend` | `celery -A config worker` |
| `beat` | misma imagen que `backend` | `celery -A config beat` |
| `web` | `nginx` (multi-stage con `node:20`) | Compila el frontend y hace de proxy inverso |

## Pasos

1. **`backend/Dockerfile`**
   ```dockerfile
   FROM python:3.13-slim
   ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
       DJANGO_SETTINGS_MODULE=config.settings.prod
   WORKDIR /app
   COPY requirements/ requirements/
   RUN pip install --no-cache-dir -r requirements/prod.txt
   COPY . .
   CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
   ```

2. **`frontend/Dockerfile`** (multi-stage)
   ```dockerfile
   FROM node:20 AS build
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build

   FROM nginx:stable
   COPY --from=build /app/dist /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   ```
   `nginx.conf` es el mismo bloque de [DESPLIEGUE.md](DESPLIEGUE.md#7-nginx)
   cambiando `proxy_pass` por `http://backend:8000` y `root` por
   `/usr/share/nginx/html`.

3. **`docker-compose.yml`** en la raíz
   ```yaml
   services:
     db:
       image: postgres:16
       env_file: backend/.env
       environment:
         POSTGRES_DB: ${POSTGRES_DB}
         POSTGRES_USER: ${POSTGRES_USER}
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
       volumes: [pgdata:/var/lib/postgresql/data]
     redis:
       image: redis:7
     backend:
       build: ./backend
       env_file: backend/.env
       environment:
         POSTGRES_HOST: db
         CELERY_BROKER_URL: redis://redis:6379/0
         CELERY_RESULT_BACKEND: redis://redis:6379/0
         MEDIA_ROOT: /data/media
       volumes: [media:/data/media, static:/app/staticfiles]
       depends_on: [db, redis]
     worker:
       build: ./backend
       command: celery -A config worker -l info
       env_file: backend/.env
       environment: { POSTGRES_HOST: db, CELERY_BROKER_URL: redis://redis:6379/0 }
       volumes: [media:/data/media]
       depends_on: [db, redis]
     beat:
       build: ./backend
       command: celery -A config beat -l info
       env_file: backend/.env
       environment: { POSTGRES_HOST: db, CELERY_BROKER_URL: redis://redis:6379/0 }
       depends_on: [db, redis]
     web:
       build: ./frontend
       ports: ["80:80", "443:443"]
       volumes: [static:/static:ro]
       depends_on: [backend]
   volumes: { pgdata: {}, media: {}, static: {} }
   ```

4. **Arranque**
   ```bash
   docker compose up -d --build
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py collectstatic --noinput
   ```

5. Agregar a `.gitignore` lo que haga falta y documentar el arranque en el
   README (criterio 15: `docker-compose up` en un entorno limpio).
