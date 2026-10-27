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
| `oferta` | `OfertaCarrera`: carrera + entidad + año académico |
| `interes` | Convocatoria de interés, expresiones de interés y endpoints públicos de la landing |
| `plan_plazas` | Plan de plazas: flujo de aprobación multinivel, historial, versión complementaria y exportaciones |
| `convocatorias` | Convocatoria de solicitud de matrícula (primera, segunda...) |
| `aspirantes` | Perfil del aspirante, tipos de documento y documentos versionados; descarga con control de acceso |
| `otorgamiento` | Ranking, reparto de plazas, ajustes manuales, aprobación y publicación (snapshot del resultado) |
| `solicitudes` | Solicitud de carreras del aspirante (selección y confirmación) y su revisión por las entidades: observaciones, validación del índice, historial, estadísticas y exportación |
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

### Convocatoria de interés y landing (RF-019 a RF-031)

**Modelo**

- `OfertaCarrera` (app `oferta`): una carrera ofertada por una Facultad o un
  CUM/FUM en un año académico (`2026-2027`). La base de datos impide repetir la
  misma carrera en la misma entidad y año. `asignada_por_ci` marca lo que
  asignó la Comisión de Ingreso: la entidad no puede quitarlo.
- `ConvocatoriaInteres`:
  - Una por año académico, con estados `borrador → abierta → cerrada`.
  - Solo puede haber una abierta a la vez (restricción de base de datos).
  - La apertura es manual: la CI la abre con al menos una carrera en la oferta.
  - El cierre es automático: la tarea `cerrar_convocatorias_vencidas`
    (Celery beat, cada hora) cierra las que pasaron su fecha de cierre.
  - Acepta interés mientras está abierta y la fecha de hoy cae dentro de su
    rango.
- `ExpresionInteres`:
  - CI, celular y email cifrados (RG-025).
  - Única por oferta y CI (RF-022): la misma persona puede interesarse por
    la misma carrera en otra entidad.
  - Al registrarla se envía la plantilla `interes_confirmado`.

**Endpoints del panel** (módulo `interes`)

| Endpoint | Quién |
|---|---|
| `/api/v1/admin/interes/convocatorias/` (+ `abrir/`, `cerrar/`) | Crear y gestionar: solo roles globales. Eliminar: solo en borrador. Una cerrada no se modifica. |
| `/api/v1/admin/interes/ofertas/?convocatoria=` | La CI agrega a cualquier entidad. Un rol local agrega a la suya (sin indicarla) y quita lo que agregó él mismo. Quitar exige `interes.editar`. |
| `/api/v1/admin/interes/expresiones/` | Interesados con sus datos personales, filtrados por el ámbito del rol. |
| `/api/v1/admin/interes/expresiones/exportar/` | Excel (RF-031, `interes.exportar`). Cada exportación se audita con los filtros y el número de registros. |

**Endpoints públicos** (sin sesión y sin datos personales)

| Endpoint | Uso |
|---|---|
| `GET /api/v1/interes/convocatoria/` | Convocatoria que hoy acepta interés, o `null`. |
| `GET /api/v1/oferta/` | Oferta de la convocatoria abierta. Filtros: `buscar`, `duracion`, `facultad`, `cum_fum`, `municipio`. |
| `GET /api/v1/carreras/` · `/carreras/{id}/` | Catálogo de carreras activas, y detalle con dónde se oferta. |
| `GET /api/v1/publico/filtros/` | Facultades, CUM/FUM y municipios para los filtros. |
| `POST /api/v1/interes/` | Registrar interés. Límite por IP: `INTERES_THROTTLE_RATE` (10/hora). |

**Landing**

- Con convocatoria abierta: aviso, oferta (una tarjeta por carrera y entidad)
  y botón "Me interesa".
- Sin convocatoria: el catálogo, sin ese botón.
- No se muestra cuántas personas están interesadas.

### Plan de plazas (RF-032 a RF-039, sección 7.3)

**Estados del plan**

`borrador → enviado → revision_ci → en_aprobacion → publicado`. Si el
Vicerrector lo devuelve, vuelve a `revision_ci`. Los estados "En revisión" y
"Propuesta enviada" de la ERS son de cada entidad, así que están en
`PlanEntidad`: `pendiente → en_revision → propuesta_enviada`.

**Quién hace qué en cada estado**

| Estado | Quién | Qué |
|---|---|---|
| borrador | CI (rol global con `plan_plazas.editar`) | Agrega carreras (manualmente o "cargar oferta del año") con su propuesta de plazas y lo envía. |
| enviado | Admin, Vicedecano o Director de cada entidad | Aceptan, modifican la cantidad o piden quitar cada línea, y solicitan carreras nuevas. Todo cambio exige comentario. Envían la propuesta, que queda bloqueada. El plan llega a todas las Facultades y CUM/FUM activos. |
| enviado | Jefe de Área | Ve el plan de su entidad y comenta; no responde ni envía. |
| enviado → revision_ci | CI | Espera a todas las entidades o fuerza el paso. Las que no enviaron conservan la propuesta inicial: sus cambios sin enviar se descartan. |
| revision_ci | CI | Decide cada línea: acepta lo propuesto por la entidad (por defecto), mantiene su propia cifra o fija otra, con comentario. Sin rondas de ida y vuelta. "Generar versión final" fija `plazas_aprobadas` y sube la versión. |
| en_aprobacion | Vicerrector (rol `vicerrector`) | **Aprobar publica directamente.** Devolver exige observaciones. |
| publicado | — | Inmutable. Se fijan las plazas en `OfertaCarrera.plazas_plan` y se crean las ofertas de las carreras nuevas aceptadas. Las que salen del plan conservan su oferta (historial de interés) sin plazas. |

- **Notificaciones**: plantillas `plan_enviado` (a quienes responden por cada
  entidad), `plan_para_aprobacion` (Vicerrector), `plan_devuelto` (CI) y
  `plan_publicado` (usuarios internos con `plan_plazas.ver`).
- **Historial** (RF-038): `HistorialPlan` guarda cada cambio con usuario,
  fecha, valor anterior, valor nuevo, comentario y versión. Los roles locales
  ven las entradas generales y las de sus líneas.
- **Versión complementaria** (RF-039): se crea desde el plan publicado
  vigente del año. Copia sus plazas aprobadas como propuesta inicial y
  recorre el flujo completo. Solo puede haber una en curso; al publicarse
  pasa a ser la vigente.
- **Acciones disponibles**: cada plan devuelve `acciones`, la lista de lo que
  el usuario actual puede hacer ahora. El frontend muestra solo esos botones;
  la API valida igualmente cada transición.
- **Concurrencia**: las transiciones bloquean la fila del plan
  (`select_for_update`) y releen su estado, para que dos acciones
  simultáneas no se pisen.
- **Exportación** (RF-037): Excel y PDF, solo del plan publicado. El PDF lleva
  membrete y la marca de aprobación visible del Vicerrector (usuario, fecha y
  hora); no es una firma criptográfica. Las exportaciones se auditan.

Endpoints: `/api/v1/admin/plan-plazas/` (+ `enviar/`, `cargar-oferta/`,
`cerrar-revision/`, `enviar-propuesta/`, `generar-version-final/`,
`aprobar/`, `devolver/`, `complementaria/`, `historial/`, `comentarios/`,
`exportar-pdf/`, `exportar-excel/`) y `/api/v1/admin/plan-plazas/lineas/?plan=`
(+ `responder/`, `decidir/`).

### Convocatoria de solicitud de matrícula (RF-040 a RF-043)

- `ConvocatoriaSolicitud`: año académico, `numero` (1.ª, 2.ª... — RF-062),
  fechas, mensaje público y entidades opcionales. Sin entidades marcadas,
  aplica a todas las que tienen plazas en el plan publicado.
- La crean y gestionan los roles globales con permiso `convocatorias.*`. El
  número se asigna solo. La siguiente exige la anterior cerrada; la condición
  de que su otorgamiento esté publicado se agrega en el feature de
  otorgamiento.
- **Abrir** (manual) exige:
  - el plan de plazas **publicado** del año;
  - carreras con plazas en las entidades elegidas;
  - que no haya otra convocatoria abierta (también restringido en la base de
    datos).
- **Cierre** automático por fecha: tarea `cerrar_convocatorias_vencidas`
  (Celery beat, cada hora).
- **Aviso a los interesados** (RF-041): al abrir la **primera** convocatoria
  del año, la tarea `notificar_interesados` escribe a quienes expresaron
  interés en la convocatoria de interés del mismo año académico, una vez por
  persona (por CI):
  - si tiene cuenta de aspirante, recibe una notificación in-app y un correo a
    la dirección de su cuenta;
  - si no, un único correo al email que dejó.

  La plantilla es `convocatoria_solicitud_abierta`. En la segunda convocatoria
  se avisa a los no seleccionados (RF-061), en su feature.
- `GET /api/v1/convocatorias/activa/` (público): convocatoria que hoy acepta
  solicitudes, o `null`. La landing muestra su aviso **por encima** del de la
  convocatoria de interés, con el botón "Solicitar matrícula".

### Portal del aspirante (RF-044 a RF-051)

**Perfil** (`apps/aspirantes`, `GET/PATCH /api/v1/aspirante/perfil/`).

- Nombre, apellidos, CI, email, celular y foto están en `Usuario`.
  `PerfilAspirante` guarda el centro de trabajo, `indice_declarado` (lo escribe
  el aspirante, 0–100) e `indice_validado` (lo cargará la entidad en
  gestión de solicitudes).
- La foto se cambia en `PATCH /auth/me/`. Para los aspirantes solo se aceptan
  JPG y PNG.
- **Perfil completo.** La fuente de verdad es
  `aspirantes.services.requisitos_perfil(perfil)`, que se recalcula a partir
  del estado real:
  - datos personales;
  - correo validado;
  - privacidad aceptada;
  - foto;
  - centro de trabajo;
  - índice declarado;
  - documentos obligatorios activos;
  - al menos una carrera.

  `PerfilAspirante.perfil_completo` es solo una caché que se actualiza con cada
  cambio. Si se agrega un documento obligatorio, los perfiles dejan de estar
  completos sin migrar nada.
- **Requisito para elegir carreras (RF-046):** todo lo anterior salvo las
  carreras (`listo_para_carreras`).

**Documentos.**

- `TipoDocumento` (nombre, obligatorio, activo, orden) lo gestiona el
  Superadmin en Configuración → Documentos del aspirante. Viene sembrado con
  *CI anverso*, *CI reverso* y *Certificación de estudios*.
- **Formatos:** PDF, JPG o PNG. Se comprueba el contenido, no la extensión.
- **Límites:** 5 MB por archivo y 20 MB por aspirante (RNF-005). La cuota
  cuenta los archivos vigentes, foto incluida.
- **Subida** (`POST /api/v1/aspirante/documentos/`): crea una **versión
  nueva**, que pasa a ser la vigente. Las anteriores se conservan como evidencia
  hasta la política de retención, como máximo 10 por documento; al superar ese
  número se borra la más antigua, con su archivo.

**Descarga** (`GET /api/v1/documentos/{id}/archivo/`). La API sirve los
archivos privados con control de acceso:

- **El propio aspirante:** solo la versión vigente.
- **El personal:** necesita el permiso `solicitudes.documentos_descargar` y,
  además:
  - ser de un rol global; o
  - que su entidad oferte alguna carrera de una solicitud **confirmada** del
    aspirante (un borrador no da acceso).

  Por semilla tienen ese permiso los roles globales, el Secretario(a) de
  Facultad, el Secretario(a) de CUM/FUM y el Director(a) de CUM/FUM.
- **Versiones anteriores:** solo los roles globales.
- **Auditoría:** cada descarga queda registrada con usuario, fecha, IP, archivo
  y un motivo automático (`consulta_documentacion` para el propio aspirante,
  `revision_solicitud` para el personal).
- **Sin acceso:** la respuesta es 404, para no revelar que el documento
  existe.

Otros endpoints con las mismas reglas:

- `GET /api/v1/admin/aspirantes/{id}/documentos/`: listado; con el historial
  para los roles globales.
- `GET /api/v1/admin/aspirantes/{id}/foto/`: la foto del aspirante.

Cada usuario pide su propia foto en `GET /api/v1/auth/me/foto/`.

**Solicitud** (`apps/solicitudes`, `/api/v1/solicitudes/`).

- **Una por aspirante y convocatoria.**
  - `POST /solicitudes/` crea el borrador en la convocatoria abierta.
  - `PUT /solicitudes/{id}/carreras/` reemplaza la selección, con las ofertas
    en orden de prioridad.
  - `POST /solicitudes/{id}/confirmar/` la presenta.
  - `GET /solicitudes/ofertas/` lista las carreras elegibles: las que tienen
    plazas en el plan publicado, dentro de las entidades de la convocatoria.
- **Reglas de la selección:**
  - de 1 al parámetro `max_carreras_aspirante`, sin repetir oferta;
  - RF-049, por tipo de entidad: una carrera puede ir en una Facultad y en un
    CUM/FUM, pero no en dos CUM/FUM (ni en dos Facultades).
- **Estados (RF-051):**
  - `borrador`: no participa;
  - `pendiente`: al confirmar;
  - `en_revision` y `observada`: los asigna la revisión de las entidades (ver
    *Gestión de solicitudes*);
  - `otorgada` y `no_seleccionado`: los asigna el otorgamiento.
- **Fechas:** `created_at` (borrador), `confirmada_at` (confirmación oficial,
  desempate del otorgamiento) y `modificada_at` (último cambio de la
  selección).
- **Al confirmar** se envía, solo esa vez, la plantilla `solicitud_confirmada`
  con el resumen, in-app y por correo. Los cambios posteriores no notifican.
- **Con la convocatoria cerrada** la solicitud y el perfil quedan congelados:
  - si la solicitud está confirmada, el aspirante ya no puede cambiar datos,
    documentos ni foto;
  - un "no seleccionado" vuelve a poder editar para la siguiente convocatoria
    (RF-062).

**Frontend** (`pages/aspirante/`):

- *Inicio*: pasos del proceso, cuenta atrás de la convocatoria y siguiente
  paso.
- *Mi perfil de aspirante* (`/aspirante/completar-perfil`): requisitos,
  datos, foto y documentos.
- *Mi solicitud* (`/aspirante/solicitud`): catálogo de carreras y selección
  ordenable con `ListaOrdenable`. Se reordena arrastrando (drag-and-drop
  nativo de HTML5), con los botones subir/bajar o con las flechas del teclado
  sobre el asa.
- Los archivos privados se piden con el token y se muestran como `blob:`
  (`useArchivoPrivado`).

### Gestión de solicitudes (RF-052 a RF-056)

**Ámbito y minimización** (`apps/solicitudes/revision.py`).

- Una entidad ve las solicitudes **confirmadas** que tienen alguna opción suya.
  De cada una ve los datos personales, el índice, los documentos, todas las
  observaciones y **solo sus opciones**: no ve carreras ni prioridades de otras
  entidades, tampoco en el historial ni en la exportación.
- Los roles globales lo ven todo.
- Ver el detalle (`GET /admin/solicitudes/{id}/`) queda auditado.

**Permisos, separados:**

- `solicitudes.ver`: listado y detalle.
- `solicitudes.editar`: revisar, es decir, validar el índice y observar.
- `solicitudes.documentos_descargar`: abrir los documentos y la foto. Sin este
  permiso se ven los datos del documento, pero no el archivo.
- `solicitudes.exportar`: Excel y PDF.

Por semilla, el Director(a) de CUM/FUM puede ver y descargar, pero no revisar.

**Estados y revisión.**

- La primera acción de revisión (validar el índice, o crear, resolver o reabrir
  una observación) pasa la solicitud de *Pendiente* a *En revisión*
  automáticamente.
- Crear una observación la pasa a *Observada*.
- Cuando el aspirante envía la corrección vuelve a *Pendiente*.
- Al resolver la última observación por corregir pasa a *En revisión*.

**Índice validado** (`POST /admin/solicitudes/{id}/validar-indice/`).

- Es obligatorio para el ranking: el declarado nunca se usa en el otorgamiento.
- Lo fija **una sola** entidad (`indice_validado_por`, `indice_validado_at`);
  después solo un rol global lo cambia.
- Se anula si el aspirante cambia su índice declarado o si una observación
  `afecta_elegibilidad`.

**Observaciones** (`POST /admin/solicitudes/{id}/observar/`,
`PATCH /admin/observaciones/{id}/`, `.../resolver/`, `.../reabrir/`).

- **Objetivo:** siempre un elemento que el aspirante puede corregir: un
  documento, el índice, el centro de trabajo o la foto. CI, nombre y correo se
  gestionan por soporte administrativo.
- **Ciclo:** `abierta` → `corregida` (el aspirante pulsa "Enviar corrección",
  `POST /solicitudes/{id}/enviar-correccion/`) → `resuelta`, o `reabierta` si
  la corrección no vale (la reapertura exige un motivo).
- **Ranking:** toda observación no resuelta (abierta, corregida o reabierta)
  saca la solicitud **completa** del ranking.
- **`afecta_elegibilidad`:** no cambia esa regla. Si es `true`, además anula el
  índice validado (hay que validarlo de nuevo) y marca la solicitud con
  `revision_documental_pendiente`, que se apaga al revalidar.
  - Valor por defecto: `true` para el índice y para los tipos de documento con
    `afecta_elegibilidad` (la certificación de estudios), `false` para el
    resto.
  - La entidad puede cambiarlo al crear la observación.
- **Visibilidad:** todas las entidades ven todas las observaciones y su autora.
  Cada entidad edita, resuelve y reabre solo las suyas; los roles globales,
  cualquiera.
- **Avisos:**
  - `solicitud_observada`, al aspirante (in-app y correo) al observar o
    reabrir;
  - `observacion_corregida`, a la autora (solo in-app) al enviar la corrección.
- **Desbloqueo selectivo.** Con la convocatoria cerrada, el aspirante puede
  corregir **solo** lo observado pendiente de corregir: ese documento, el
  índice, el centro de trabajo o la foto. Nunca carreras ni prioridades.

**Historial (RF-054, `EventoHistorial`).** Se guarda con usuario y fecha:

- la selección de carreras al guardar, antes y después;
- la confirmación;
- los documentos subidos o sustituidos, con la versión anterior y la nueva;
- los cambios de datos del perfil;
- la validación del índice;
- creación, edición, corrección, resolución y reapertura de observaciones.

**Elegibilidad.** `revision.motivos_no_elegible(solicitud)` devuelve por qué
la solicitud no entraría hoy en el ranking:

- estado distinto de *Pendiente* o *En revisión*;
- observaciones sin resolver;
- índice sin validar;
- perfil incompleto.

La usará el otorgamiento.

**Listado, estadísticas y exportación.**

- `GET /admin/solicitudes/` admite los filtros de RF-052: convocatoria,
  carrera, entidad, estado, rango de fechas de confirmación y rango de índice
  (el validado o, si falta, el declarado). Además: con observaciones sin
  resolver, nombre o CI completo (por hash) y orden por índice o nombre.
- `GET /admin/solicitudes/estadisticas/` (RF-053):
  - termómetro con las solicitudes de cada oferta frente a sus plazas (y
    cuántas en 1.ª opción);
  - distribución por carrera;
  - evolución diaria de confirmaciones;
  - totales por estado.

  El panel la consulta cada 60 s con la pestaña visible (`usePolling`). Los
  gráficos son SVG y CSS propios (`components/graficos/`).
- `GET /admin/solicitudes/exportar-excel/` y `.../exportar-pdf/` (RF-056):
  aplican los mismos filtros e incluyen solo las opciones del ámbito. Se
  auditan.

**Frontend:**

- `/admin/solicitudes`: listado y estadísticas.
- `/admin/solicitudes/:id`: datos, índice, documentos con visor inline de PDF e
  imagen, observaciones e historial.
- Portal del aspirante:
  - observaciones en *Mi solicitud*, con "Enviar corrección";
  - elementos observados resaltados y desbloqueados en *Mi perfil de
    aspirante*.

### Otorgamiento de plazas (RF-057 a RF-064)

**Etapas** (`apps/otorgamiento`). Los permisos van por etapa, no por código de
rol:

1. **Generar** (`otorgamiento.generar`, Secretaría General): con la
   convocatoria cerrada, `GET /admin/otorgamiento/previsualizar/?convocatoria=`
   muestra cuántas solicitudes son elegibles, cuántas no y por qué. Después,
   `POST /admin/otorgamiento/` con `confirmar: true` genera el ranking y el
   reparto. Solo se ejecuta una vez por convocatoria.
2. **Revisión del Jefe CI** (`otorgamiento.aprobar`): revisa, ajusta y aprueba.
3. **Aprobación del Vicerrector** (`otorgamiento.publicar`): revisa, ajusta y
   aprueba. Su aprobación **publica**. El diálogo pregunta si habrá segunda
   convocatoria.

**Elegibilidad y ranking.**

- Entran al ranking solo las solicitudes elegibles (ver
  `revision.motivos_no_elegible`); las demás quedan fuera con su motivo.
- Orden del ranking: índice **validado** de mayor a menor, luego
  `confirmada_at` y, como desempate técnico, el id.
- Reparto (`algoritmo.repartir`, una función pura): cada aspirante recibe una
  sola plaza, la de mayor prioridad que tenga plaza libre.
- Nunca se otorga plaza a un no elegible, ni en el reparto automático ni en
  un ajuste manual.

**Ajustes manuales** (`POST /admin/otorgamiento/{id}/ajustar/`).

- Tipos:
  - `otorgar`: fija al aspirante en una de **sus** opciones; si tenía otra,
    la pierde;
  - `quitar`: le impide esa opción, y el reparto le da la siguiente si
    alcanza.
- Cada ajuste exige justificación.
- Tras cada ajuste el reparto se recalcula: primero los ajustes vigentes y
  después el algoritmo, por orden de ranking, cubre las vacantes. Así se
  resuelven las cascadas, y el aspirante desplazado baja a su siguiente opción.
- Nunca se supera el plan: si los ajustes fijados no caben, se rechaza.
- La respuesta incluye los `cambios` del reparto.
- Un ajuste se puede anular, también con justificación.

**Snapshot** (`ResultadoOtorgamiento`).

- Una fila por solicitud confirmada, con aspirante, índice utilizado, posición
  en el ranking, motivo de exclusión, opciones tal como estaban y lo otorgado
  (carrera, entidad, prioridad, automático o manual).
- `Otorgamiento.capacidad` guarda las plazas disponibles al generar y
  `resumen`, la elegibilidad que se confirmó.
- Al publicar queda congelado. Los informes históricos leen el snapshot,
  nunca las solicitudes actuales.
- Generado el otorgamiento, la revisión de esa convocatoria se cierra: no hay
  más validaciones, observaciones ni correcciones en ella.

**Visibilidad.**

- **Antes de publicar:** solo los roles globales ven el resultado
  provisional; el aspirante no ve nada.
- **Al publicar:** las solicitudes pasan a *Otorgada* o *No seleccionado*,
  cada opción a otorgada o no seleccionada, y se avisa:
  - `plaza_otorgada` (RF-060);
  - `no_seleccionado_segunda` o `no_seleccionado_final` (RF-061), según la
    casilla de segunda convocatoria.

  Las entidades ven entonces lo otorgado en ellas.

**Segunda convocatoria (RF-062).**

- Solo se crea con la anterior cerrada **y** su otorgamiento publicado.
- Ofrece las ofertas con plazas restantes (plan menos lo otorgado y publicado
  en convocatorias anteriores, `services.plazas_restantes`).
- Los no seleccionados pueden presentar una solicitud nueva; los otorgados
  no.

**Exportación (RF-063):** `.../exportar-excel/` (todos los resultados) y
`.../exportar-pdf/` (otorgados por carrera y entidad, con el sello de
publicación). Se auditan. El listado público en la landing va en el feature
`resultados-publicos`.

### Exportar a PDF

`apps.core.pdf.respuesta_pdf(plantilla, contexto, nombre, titulo)` renderiza
una plantilla que extiende `pdf/base.html`, con el membrete de RE-009:
escudo, institución, sistema, fecha de generación y número de página.

WeasyPrint se importa al usarse. Si faltan sus librerías nativas, el sistema
funciona igual y solo la exportación responde con un error claro. Las pruebas
del PDF se saltan solas en ese caso. Instalación: ver
[DESPLIEGUE.md](DESPLIEGUE.md#librerías-de-weasyprint-pdf).

### Exportar a Excel

`apps.core.excel.respuesta_excel(nombre, titulo, columnas, filas)` genera un
`.xlsx` con:
- encabezado con institución, sistema, título y fecha de generación;
- cabecera de la tabla con el color primario de la identidad visual;
- filtros y paneles fijos.

Toda exportación con datos personales debe registrarse con
`apps.auditoria.services.registrar`. En el frontend, el archivo se pide con
`responseType: 'blob'` y se descarga con `utils/descargar.js`.

### Archivos

| Almacenamiento | Carpeta | Contenido | Quién lo sirve |
|---|---|---|---|
| `default` (privado) | `MEDIA_ROOT` | Fotos y documentos de los usuarios | Solo la API, con permisos (ver *Portal del aspirante*) |
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
- Consulta: `GET /api/v1/admin/logs/` con los filtros `usuario` (id),
  `usuario_nombre`, `accion`, `modulo`, `resultado`, `desde` y `hasta`.
  `GET /api/v1/admin/logs/modulos/` devuelve los módulos que aparecen en el log.
  Exige `logs.ver`, que en la matriz inicial tienen solo el Superadmin y el
  Jefe CI.
- En el panel: "Logs de auditoría", de solo lectura, con un detalle de cada
  registro.

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
