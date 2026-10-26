# Entorno de desarrollo

## Requisitos

- Python 3.12 o superior
- Node.js 20 o superior (con npm)
- Git
- Redis (opcional en desarrollo, ver más abajo)

## Backend

```bash
cd backend
python -m venv .venv

# Activar el entorno virtual
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements/dev.txt
cp .env.example .env        # opcional en desarrollo: hay valores por defecto
python manage.py migrate
python manage.py createsuperuser   # Superadmin para entrar al panel
python manage.py runserver  # http://localhost:8000
```

Por defecto `manage.py` usa `config.settings.dev`, que trabaja con SQLite
(`backend/db.sqlite3`) y no necesita ninguna variable de entorno obligatoria.

En desarrollo los correos (p. ej. el de activación de cuenta) se imprimen en la
consola del `runserver` en lugar de enviarse.

Comprobación rápida: `http://localhost:8000/api/v1/health/` debe responder
`{"status": "ok"}`.

### Pruebas

```bash
cd backend
pytest
```

Muestra el reporte de cobertura al final. La meta del proyecto es ≥ 70 %.

Las pruebas que generan PDF reales se saltan si WeasyPrint no encuentra sus
librerías nativas (Pango/GTK), lo habitual en Windows. Para ejecutarlas,
instálalas como se indica en
[DESPLIEGUE.md](DESPLIEGUE.md#librerías-de-weasyprint-pdf).

### Celery en desarrollo

En desarrollo `CELERY_TASK_ALWAYS_EAGER=True` (valor por defecto) hace que las
tareas se ejecuten en el mismo proceso, sin Redis. Para probar las tareas
programadas de verdad:

1. Instalar y arrancar Redis (en Windows se puede usar WSL o Memurai).
2. En `backend/.env`: `CELERY_TASK_ALWAYS_EAGER=False`.
3. En dos terminales con el entorno virtual activo:
   ```bash
   celery -A config worker -l info
   celery -A config beat -l info
   ```
   En Windows el worker necesita `--pool=solo`.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Vite redirige las peticiones a `/api` hacia `http://localhost:8000`, así que el
backend debe estar corriendo.

Otros comandos:

| Comando | Qué hace |
|---|---|
| `npm test` | Ejecuta las pruebas con Vitest |
| `npm run test:watch` | Pruebas en modo observación |
| `npm run lint` | Revisa el código con oxlint |
| `npm run build` | Compila a `frontend/dist/` para producción |
