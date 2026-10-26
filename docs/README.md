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
| `nomencladores` | Municipios, Facultades, CUM/FUM, Áreas, Departamentos, Cargos y catálogo global de Carreras |
| `configuracion` | Parámetros del sistema, SMTP, plantillas de correo e identidad visual |
| `notificaciones` | Notificaciones in-app y por correo, envíos masivos |
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
- `GET /api/v1/admin/usuarios/roles-asignables/` (permiso `usuarios.ver`)
  devuelve los roles que el usuario actual puede asignar, sin exigir
  `roles.ver`:
  - el Superadmin recibe todos;
  - los demás, solo roles locales;
  - un rol local, solo los de su mismo ámbito.
### Ámbito de datos: global y local (RG-027, criterio 11)

- Un usuario con rol local pertenece a una Facultad (`usuario.facultad`) **o** a
  un CUM/FUM (`usuario.cum_fum`). Una restricción de base de datos
  (`usuario_una_sola_entidad`) impide que tenga ambas. La API valida además que
  cada rol local tenga exactamente la entidad de su ámbito: una `CHECK` no
  puede leer la tabla de roles. Los Jefes de Área (`rol.requiere_area`) tienen
  además un área de esa entidad.
- `apps.core.ambito.filtrar_por_entidad(qs, usuario, campo_facultad, campo_cum_fum)`
  es el filtro que debe aplicar **todo** módulo con datos por entidad:
  - Los roles globales ven todo.
  - Los locales ven solo lo de su entidad.
  - Un rol local sin entidad asignada no ve nada.
- `es_de_su_entidad(usuario, facultad, cum_fum)` comprueba las escrituras.
- Hoy lo aplican los usuarios internos, las áreas y los departamentos.

### Nomencladores

- Rutas: `/api/v1/admin/nomencladores/{municipios,facultades,cum-fum,areas,departamentos,cargos,carreras}/`.
  Filtros comunes: `activo`, `buscar`. Algunos tienen filtros propios
  (`municipio`, `tipo`, `facultad`, `cum_fum`, `area`, `duracion`).
- Leer exige `nomencladores.ver`. Para escribir:
  - Los catálogos globales (municipios, facultades, CUM/FUM, cargos, carreras)
    solo los modifican los roles globales, aunque un rol local tenga
    `nomencladores.crear` o `nomencladores.editar`.
  - Las áreas y los departamentos los gestiona cada entidad.
- Un registro en uso no se puede borrar (`PROTECT`): se desactiva con
  `PATCH {"activo": false}`.
- Los 14 municipios de Holguín se precargan en la migración
  `nomencladores/0002`.
- La carrera es un catálogo global. Qué entidad la oferta cada año lo define
  `OfertaCarrera`, que llega con la convocatoria de interés.

### Configuración del sistema

Leer exige `configuracion.ver`. Modificar exige además ser **Superadmin**, aunque
otro rol tenga `configuracion.editar`.

| Endpoint | Contenido |
|---|---|
| `GET/PATCH /api/v1/admin/configuracion/parametros/` | Máximo de carreras por aspirante (RF-007), intentos de login y minutos de bloqueo (RF-008). Los valores iniciales salen de `LOGIN_MAX_INTENTOS` y `LOGIN_BLOQUEO_MINUTOS`; después manda la base de datos. |
| `GET/PATCH /api/v1/admin/configuracion/smtp/` | Servidor de correo (RF-009, RE-010). |
| `POST /api/v1/admin/configuracion/smtp/probar/` | `{destinatario}`. Envía un correo de prueba con la configuración guardada. |
| `GET/PATCH /api/v1/admin/configuracion/plantillas/{codigo}/` | Texto de una plantilla de correo (RF-011). |
| `POST .../plantillas/{codigo}/vista-previa/` | `{asunto, cuerpo}` con valores de ejemplo. |
| `POST .../plantillas/{codigo}/restablecer/` | Vuelve al texto por defecto. |
| `GET/PATCH /api/v1/admin/configuracion/identidad/` | Nombre de la institución, tres colores y escudo. |
| `GET /api/v1/identidad/` | Lo mismo, público. El frontend lo pide al arrancar. |

- **SMTP**:
  - Si en el panel está marcado "usar esta configuración", se usa esa; si no,
    se usan las variables `EMAIL_*` del `.env`.
  - La contraseña se guarda cifrada con AES-256 (la misma clave de RG-025)
    porque el sistema necesita leerla. La API la acepta pero nunca la
    devuelve: solo informa `password_configurada`. Si se envía vacía, se
    conserva la guardada.
  - El modelo no está registrado en el admin de Django.
- **Plantillas**:
  - Asunto y cuerpo en texto plano, con variables `{{ variable }}`. La
    sustitución es propia, no usa el motor de plantillas de Django: no se
    pueden usar etiquetas `{% ... %}`.
  - La API rechaza las variables que la plantilla no admite.
  - El catálogo (`apps/configuracion/catalogo_plantillas.py`) fija las
    variables y el texto por defecto de cada plantilla.
  - **Para agregar un correo nuevo**:
    1. Añadir la entrada en el catálogo.
    2. Crear una migración de datos que cree la fila.
    3. Enviarlo con `apps.configuracion.services.enviar_correo(codigo, destinatarios, contexto)`.
- **Identidad visual**: `IdentidadProvider` (frontend) sobrescribe
  `--color-primary`, `--color-primary-light` y `--color-accent` al arrancar y al
  guardar. Si la API no responde, quedan los valores de `tokens.css`. El escudo
  se guarda en el almacenamiento público.

### Notificaciones (RF-073 a RF-076)

| Endpoint | Uso |
|---|---|
| `GET /api/v1/notificaciones/?leida=` | Notificaciones propias, paginadas. Cada usuario ve solo las suyas; no exige permisos de módulo. |
| `GET /api/v1/notificaciones/no-leidas/` | `{no_leidas}`. Es la consulta del polling de la campana. |
| `POST /api/v1/notificaciones/{id}/leer/` · `POST .../leer-todas/` · `DELETE .../{id}/` | Marcar como leída o borrar. |
| `GET/POST /api/v1/admin/notificaciones/envios/` | Historial y creación de envíos masivos (`notificaciones.ver` / `notificaciones.crear`). |
| `POST /api/v1/admin/notificaciones/envios/contar/` | Número de destinatarios de un grupo, antes de enviar. |

- **Automáticas** (RF-075): los módulos llaman a
  `apps.notificaciones.services.notificar(usuarios, codigo_plantilla, contexto)`.
  - Crea la notificación in-app y envía por correo el mismo texto, sacado de
    la plantilla.
  - `contexto` puede ser un dict o una función `usuario -> dict` para
    variables distintas por destinatario. `nombre` se rellena solo.
  - El correo se envía en la tarea de Celery `enviar_correos`, con una sola
    conexión SMTP por lote. Si falla un destinatario, se registra en el log y
    se continúa con el resto.
- **Masivas** (RF-076):
  - Grupos: `{"tipo": "rol", "rol": codigo}`,
    `{"tipo": "entidad", "facultad"|"cum_fum": id}` y `{"tipo": "aspirantes"}`.
  - Solo reciben usuarios activos; los aspirantes, además, con la cuenta
    verificada.
  - Los roles locales solo envían dentro de su entidad: su grupo "entidad" es
    siempre la suya y no pueden usar "aspirantes". Cada uno ve solo el
    historial de su entidad.
  - El texto admite `{{ nombre }}`. El correo es opcional (por defecto, no).
  - Cada envío queda registrado en `EnvioMasivo`.
- **Frontend**:
  - `NotificacionesProvider` (dentro de los layouts del panel y del portal)
    consulta el contador cada 60 s y solo con la pestaña visible.
  - El polling no mantiene viva la sesión: la renovación depende de la
    actividad del usuario.
  - Las notificaciones no se borran automáticamente; el usuario las borra.

### Archivos

| Almacenamiento | Carpeta | Contenido | Quién lo sirve |
|---|---|---|---|
| `default` (privado) | `MEDIA_ROOT` | Fotos y documentos de los usuarios | Solo la API, con permisos (pendiente: endpoint de descarga) |
| `publico` | `PUBLIC_MEDIA_ROOT` | Imágenes de carreras, facultades y CUM/FUM | nginx en `/media/` (en desarrollo, Django) |

Un campo público se declara con `storage=almacenamiento_publico`
(`apps.core.storage`). El admin de Django está en `/django-admin/`, porque
`/admin` es el panel de React.

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

### Pantallas CRUD

`components/crud/CrudPage` es una pantalla completa de listado y edición,
configurable. Incluye:
- búsqueda diferida, filtros y paginación;
- alta y edición en un modal, con un formulario generado desde un esquema de
  campos;
- activar y desactivar;
- baja con confirmación.

La usan los nomencladores (`pages/admin/nomencladores/`). Para un recurso nuevo:

```jsx
const recurso = crearRecurso('/admin/algo/')       // services/recursos.js
<CrudPage
  titulo="Algo" singular="algo" recurso={recurso}
  columnas={[{ key: 'nombre', header: 'Nombre' }]}
  campos={[{ name: 'nombre', label: 'Nombre', required: true }]}
  valoresIniciales={{ nombre: '' }}
  permisos={{ crear: true, editar: true, eliminar: false }}
/>
```

Otras opciones de `CrudPage`:

| Opción | Para qué sirve |
|---|---|
| `campos` como función `(valores) => [...]` | Mostrar campos según lo elegido, p. ej. la Facultad solo si el rol es de Facultad. |
| `type: 'checkbox'` | Campo de casilla. |
| `type: 'custom'` con `render({value, onChange, error})` | Un control propio, como la matriz de permisos. |
| `nombreDe(item)` | Texto con el que se nombra el registro. |
| `estado` | Cómo se lee y alterna el estado. Usuarios usa bloquear/desbloquear en lugar de `activo`. |
| `accionesExtra(item, recargar)` | Botones adicionales por fila. |
| `puedeEliminarItem(item)` | Ocultar "Eliminar" en registros concretos, como los roles del sistema. |

`crearRecurso` envía JSON, o multipart si algún valor es un `File`. Con
imágenes, `aDatos={omitirArchivoSinCambios}` evita reenviar la que ya estaba
guardada.

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
