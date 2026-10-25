# Documentación de SIGECUE

Sistema de Gestión de Carreras por Encuentro de la Universidad de Holguín (UHO).
Cubre el ciclo de ingreso a las carreras por encuentro: oferta académica,
expresión de interés, plan de plazas, convocatoria de solicitud, otorgamiento
de plazas y prematrícula.

## Índice

| Documento | Contenido |
|---|---|
| [DESARROLLO.md](DESARROLLO.md) | Cómo levantar el proyecto en una máquina local |
| [DESPLIEGUE.md](DESPLIEGUE.md) | Cómo instalar y poner en producción en Linux, macOS o Windows |
| [DOCKER.md](DOCKER.md) | Cómo contenerizar el sistema más adelante (pendiente de implementar) |
| [GIT.md](GIT.md) | Flujo de ramas y formato de commits |
| [DECISIONES.md](DECISIONES.md) | Decisiones del cliente que se apartan o precisan la ERS |
| [ANOTACIONES.md](ANOTACIONES.md) | Elementos provisionales y pendientes de material externo |

## Arquitectura

```
navegador ──► nginx ──┬──► frontend/dist (React compilado, archivos estáticos)
                      └──► /api, /admin ──► gunicorn ──► Django + DRF ──► PostgreSQL
                                                              │
                                                              └──► Redis ◄── Celery (worker + beat)
```

- **backend/** — API REST con Django + Django REST Framework.
  - `config/`: configuración del proyecto. `settings/base.py` es común;
    `dev.py` (SQLite, depuración) y `prod.py` (PostgreSQL, HTTPS) la extienden.
  - `apps/`: una app de Django por dominio (`core`, y las que se agreguen
    por feature). Cada app separa modelos, serializers, vistas y, si la lógica
    es compleja, `services.py`.
  - Todas las rutas de la API cuelgan de `/api/v1/`.
- **frontend/** — SPA con React + Vite.
  - `src/components/`: componentes reutilizables.
  - `src/pages/`: pantallas.
  - `src/hooks/`: hooks propios.
  - `src/services/`: acceso a la API.
  - `src/styles/tokens.css`: único CSS global (variables de diseño y reset).
    El resto de los estilos usa CSS Modules (`Componente.module.css`).
### Apps del backend

| App | Responsabilidad |
|---|---|
| `core` | Piezas transversales: formato de errores, paginación, modelos base, cifrado de datos personales |
| `users` | Modelo de usuario (`AUTH_USER_MODEL = users.Usuario`) |
| `auditoria` | Log de auditoría inmutable (RG-010) |

### API

- Documentación interactiva (Swagger UI): `/api/docs/`. Esquema OpenAPI: `/api/schema/`.
- Errores: todas las respuestas de error tienen el mismo formato, con un
  mensaje en español pensado para mostrarse al usuario (RG-003):
  ```json
  {"error": {"codigo": "invalid", "mensaje": "Revisa los datos marcados e inténtalo de nuevo.",
             "detalles": {"ci": ["El CI debe tener 11 dígitos."]}}}
  ```
  Los services lanzan `apps.core.exceptions.ErrorDeNegocio("mensaje")` cuando
  una operación incumple una regla del proceso.
- Paginación: `?page=N&page_size=M` (máximo 100). Respuesta
  `{"count", "next", "previous", "results"}`.

### Datos personales cifrados (RG-025)

CI, celular y email se guardan con `apps.core.fields.CampoCifrado` (AES-256-GCM).
Como el texto cifrado cambia en cada guardado, no se puede buscar ni exigir
unicidad sobre esa columna. Para eso cada dato que lo necesite (el CI) tiene al
lado una columna con `apps.core.crypto.hash_busqueda(valor)`, un HMAC-SHA256
determinista. Las claves están en `FIELD_ENCRYPTION_KEY` y `SEARCH_HASH_KEY`.

### Auditoría (RG-010)

- **Automática**: el middleware `AuditoriaMiddleware` registra toda petición
  a `/api/v1/` con método POST, PUT, PATCH o DELETE: usuario, acción
  (método + ruta), módulo, id afectado, IP, resultado y código HTTP.
- **Explícita**: los services llaman a `apps.auditoria.services.registrar(...)`
  para eventos de negocio y para lecturas sensibles (p. ej. consultar datos
  personales de un aspirante, RG-027). Las lecturas normales no se registran
  solas, porque el polling de notificaciones generaría miles de registros por
  minuto.
- La aplicación impide modificar o borrar registros de auditoría mediante la
  API, el panel de administración y las operaciones normales del ORM. Quien
  tenga acceso directo al código o a la base de datos puede saltarse esa
  restricción. Para reforzarla en producción se puede agregar un trigger de
  PostgreSQL que rechace `UPDATE`/`DELETE` sobre la tabla y conectar la
  aplicación con un usuario de base de datos sin esos privilegios.
- Consulta: `GET /api/v1/admin/logs/` con filtros `usuario`, `accion`, `modulo`,
  `resultado`, `desde`, `hasta`.

### Tareas en segundo plano

- **Celery + Redis** — tareas programadas (cierre automático de convocatorias,
  limpieza de cuentas no activadas, recordatorios, etc.).
