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
| [SGU.md](SGU.md) | Cómo conectar la autenticación con auth.uho.edu.cu |
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
| `roles` | Roles, catálogo de permisos (módulo × acción) y la clase `PermisoModulo` |
| `users` | Usuario (`AUTH_USER_MODEL = users.Usuario`), autenticación, registro de aspirantes, gestión de usuarios internos |
| `auditoria` | Log de auditoría (RG-010) |

### Autenticación

| Endpoint | Uso |
|---|---|
| `POST /api/v1/auth/login/` | `{identificador, password}`. Aspirantes con su email, internos con su usuario. Devuelve `{access, usuario}` y deja la cookie de refresh. |
| `POST /api/v1/auth/refresh/` | Sin cuerpo. Lee la cookie, devuelve un `access` nuevo y rota la cookie. |
| `POST /api/v1/auth/logout/` | Invalida el refresh y borra la cookie. |
| `POST /api/v1/auth/registro/` | Registro de aspirante. Envía el correo de activación. |
| `POST /api/v1/auth/activar/` | `{token}` recibido en el correo. |
| `GET/PATCH /api/v1/auth/me/` | Perfil propio con rol y permisos. Editables: `celular`, `foto`. |
| `POST /api/v1/auth/me/password/` | `{actual, nueva}`. No aplica a usuarios del SGU. |

- **Tokens**: el `access` (JWT, 15 min) se manda como `Authorization: Bearer ...`
  y el frontend lo guarda **solo en memoria**. El refresh (8 h) va en la cookie
  `sigecue_refresh`: `httpOnly`, `SameSite=Strict`, `Secure` en producción y
  limitada a `/api/v1/auth/`. JavaScript no puede leerla. Se rota en cada uso,
  así que la sesión caduca tras 8 h sin renovarse o al cerrar sesión (RG-011).
- **Importante para el frontend**: renovar el access solo cuando hay actividad
  del usuario. Si el polling de notificaciones renovara la sesión por su
  cuenta, una pestaña abierta nunca caducaría por inactividad.
- **Bloqueo temporal** (RG-009): tras `LOGIN_MAX_INTENTOS` fallos seguidos la
  cuenta queda bloqueada `LOGIN_BLOQUEO_MINUTOS`. Los endpoints públicos de auth
  tienen además un límite de peticiones por IP (`AUTH_THROTTLE_RATE`).
- **Contraseñas**: Argon2 (RG-007) y validadores de Django.
- **Cuentas no activadas**: la tarea `eliminar_cuentas_no_verificadas` (Celery
  beat, cada hora) borra los aspirantes que no activaron su cuenta en 48 h.

### Permisos

- Cada rol tiene permisos `modulo.accion` (catálogo en `apps/roles/catalogo.py`).
  El Superadmin tiene acceso total sin necesidad de permisos.
- Los 13 roles de la ERS se crean en la migración `roles/0002_roles_iniciales`
  con una matriz inicial. El Superadmin puede editar sus permisos, crear roles
  nuevos y desactivarlos, pero no borrar ni cambiar el código o ámbito de los
  13 roles del sistema.
- En una vista: `permission_classes = [PermisoModulo]` y `modulo = "..."`.
  `list`/`retrieve` exigen `ver`, `create` exige `crear`, `update` exige
  `editar` y `destroy` exige `eliminar`. Las acciones propias se declaran en
  `acciones_permiso`; si una acción no está declarada, se deniega.
- Por defecto, toda vista de la API exige sesión iniciada
  (`DEFAULT_PERMISSION_CLASSES`). Las públicas lo declaran explícitamente.
- `GET /api/v1/admin/roles/catalogo/` devuelve los permisos agrupados por módulo
  para construir la matriz en el panel.
- **Pendiente** (feature `nomencladores`): vincular a los usuarios locales con su
  Facultad o CUM/FUM y filtrar los datos por ámbito (RG-027, criterio 11).

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

## Frontend

### Estructura (`frontend/src/`)

| Carpeta | Contenido |
|---|---|
| `components/ui/` | Sistema de diseño genérico: `Button`, `Badge`/`StatusBadge`, `Card`, `KpiCard`, `Alert`, `Input`/`Select`/`Textarea`/`Checkbox`, `Modal`, `DataTable`, `Pagination`, `Stepper`, `Avatar`, `Spinner`, `EmptyState`, `PageHeader`, `Toast`. Se importan desde `components/ui`. |
| `components/layout/` | `PublicLayout`, `AdminLayout` (sidebar + barra superior), `AspiranteLayout`, `RequireAuth`, `UserMenu`, `NotificationBell`, `Logo`, `AuthCard`. El menú del panel está en `Sidebar/menuAdmin.js`. |
| `pages/` | Pantallas, agrupadas en `public/`, `auth/`, `admin/`, `aspirante/`, `cuenta/` y `errores/`. |
| `hooks/` | `useAuth` (sesión, `tienePermiso`) y `useFormulario` (valores, errores de la API, envío). |
| `services/` | Acceso a la API: `api.js` (cliente axios), `auth.js`, `perfil.js`, `errores.js`. |
| `utils/` | Funciones puras pequeñas (`cx`, `iniciales`). |
| `router.jsx` | Todas las rutas. |
| `styles/tokens.css` | Único CSS global: variables de diseño y reset. |

### Reglas de estilo

- Cada componente tiene su `Componente.module.css`. Nada de estilos inline ni
  de clases globales.
- Colores, espacios, radios y tipografía salen de las variables de `tokens.css`
  (`var(--color-primary)`, `var(--space-4)`...). La identidad visual guardada en
  base de datos sobrescribirá esas variables al cargar la app (pendiente:
  feature `system-config`).
- Mobile-first (RE-003): estilos base para 320 px y `@media (min-width: ...)`
  para 768 px y 1024 px.
- Accesibilidad (RG-005): etiquetas asociadas a cada campo, errores enlazados
  con `aria-describedby`, foco gestionado en los modales y enlace "Saltar al
  contenido" en el panel.

### Sesión en el navegador

- El access token vive solo en memoria (`services/tokenStore.js`). Al recargar
  la página, `AuthProvider` recupera la sesión con la cookie de refresh.
- Ante un 401, `services/api.js` renueva el token una sola vez (las peticiones
  simultáneas comparten la renovación) y repite la petición.
- **Inactividad**: `services/actividad.js` registra la última interacción del
  usuario (clic, tecla, rueda, toque). Si pasaron más de 8 h, no se renueva y
  la sesión se da por caducada. Así el polling no mantiene viva una pestaña
  abandonada.
- `RequireAuth tipo="interno" | "aspirante"` y `permiso="modulo.accion"`
  protegen las rutas. Es solo una ayuda de interfaz: la API valida cada
  petición.

### Añadir la pantalla de un módulo del panel

1. Crear la página en `pages/admin/`.
2. Registrarla en `PANTALLAS_ADMIN` dentro de `router.jsx`, con el mismo `path`
   que tiene en `menuAdmin.js`. La ruta, el permiso y la entrada del sidebar ya
   salen del menú.

### Pruebas

- `src/**/*.test.jsx` con Vitest y Testing Library.
- `src/test/renderApp.jsx` monta la app completa en una ruta, con un router en
  memoria, para probar flujos (login, rutas protegidas...).

### Tareas en segundo plano

- **Celery + Redis** — tareas programadas (cierre automático de convocatorias,
  limpieza de cuentas no activadas, recordatorios, etc.).
