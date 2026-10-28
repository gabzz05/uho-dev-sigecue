# SIGECUE

**Sistema de Gestión de Carreras por Encuentro** de la Universidad de Holguín.

Gestiona el ingreso a las carreras por encuentro de principio a fin:

1. oferta académica y expresión de interés de la población;
2. plan de plazas;
3. convocatoria de solicitud;
4. revisión de solicitudes;
5. otorgamiento de plazas;
6. resultados públicos;
7. prematrícula.

Implementa la ERS v1.0. El estado de cada requisito está en
[docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md).

## Módulos

| Módulo | Qué hace |
|---|---|
| Landing pública | Carreras, expresión de interés, avisos de convocatoria y consulta de resultados |
| Portal del aspirante | Registro, perfil con documentos, solicitud de carreras por prioridad y prematrícula |
| Interés | Convocatoria de interés, oferta por entidad, interesados y dashboard con mapa por municipio |
| Plan de plazas | Flujo CI → entidades → CI → Vicerrector, con historial, versión complementaria y PDF |
| Solicitudes | Revisión por las entidades: validación del índice, observaciones, historial y estadísticas |
| Otorgamiento | Ranking por índice, reparto automático, ajustes con justificación, aprobación y publicación |
| Prematrícula | Período, expediente con revisión por documento, correcciones y aprobación |
| Administración | Usuarios, roles y permisos, nomencladores, configuración, notificaciones, auditoría y retención de datos |

## Tecnología

- **Backend** (`backend/`): Django + Django REST Framework, PostgreSQL (SQLite
  en desarrollo) y Celery + Redis.
- **Frontend** (`frontend/`): React + Vite y CSS Modules.
- **Despliegue:** Docker Compose (PostgreSQL, Redis, backend, worker y beat de
  Celery, y nginx con HTTPS).

API documentada en `/api/docs/`.

## Despliegue con Docker (recomendado)

Solo hace falta Docker con Compose en el host.

```bash
cp .env.example .env
docker compose run --rm --no-deps backend claves   # pegar las 3 claves en .env
docker compose up -d --build                       # https://localhost
```

Después, abrir **https://localhost** y entrar en `/login` con el usuario y la
contraseña de `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` del
`.env`. Hasta que se instale el certificado de la UHO en `./certs/`, nginx usa
uno autofirmado y el navegador avisa de que no es de confianza: aceptar y
continuar.

Detalle, certificado TLS y copias de seguridad en [docs/DOCKER.md](docs/DOCKER.md).

## Arranque rápido (desarrollo)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver

# Frontend (otra terminal)
cd frontend
npm install && npm run dev                           # http://localhost:5173
```

Detalle en [docs/DESARROLLO.md](docs/DESARROLLO.md).

## Documentación

| Documento | Para qué |
|---|---|
| [docs/README.md](docs/README.md) | Funcionamiento de cada módulo |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Arquitectura real: apps, flujo, Celery, archivos, auditoría |
| [docs/MANUAL.md](docs/MANUAL.md) | Qué hace cada rol en cada etapa |
| [docs/DESARROLLO.md](docs/DESARROLLO.md) | Entorno local y pruebas |
| [docs/DOCKER.md](docs/DOCKER.md) | Despliegue con Docker Compose (recomendado) |
| [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) | Producción sin Docker en Linux, macOS o Windows |
| [docs/DECISIONES.md](docs/DECISIONES.md) | Decisiones del cliente y desviaciones de la ERS |
| [docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md) | Requisito → implementación |
| [docs/ANOTACIONES.md](docs/ANOTACIONES.md) | Pendientes que debe aportar la UHO |
| [docs/SGU.md](docs/SGU.md) · [docs/GIT.md](docs/GIT.md) | Integración con el SGU y flujo de Git |
