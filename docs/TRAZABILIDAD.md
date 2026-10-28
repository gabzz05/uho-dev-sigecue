# Matriz de trazabilidad — ERS v1.0

Qué requisito de la ERS cubre cada parte del sistema. Los estados posibles son:

- **Sí:** está implementado y probado.
- **Decisión:** se implementó distinto de la ERS por una decisión del cliente;
  el motivo está en [DECISIONES.md](DECISIONES.md).
- **Parcial:** una parte está hecha y otra depende de material o sistemas
  externos.
- **Documentado:** es una tarea de operación descrita en
  [DESPLIEGUE.md](DESPLIEGUE.md).
- **No verificado:** requiere medirse en la infraestructura de la UHO.
- **No:** no está implementado.

Las apps citadas están en `backend/apps/` y las pantallas en `frontend/src/pages/`.

Pruebas automatizadas: 526 en el backend (cobertura del 96 %) y 192 en el
frontend. La cobertura del frontend no se mide: no hay herramienta de
cobertura entre las librerías aprobadas.

## Requisitos funcionales

| ID | Requisito | Estado | Dónde |
|---|---|---|---|
| RF-001 | CRUD de Facultades | Sí | `nomencladores`; Administración → Facultades / CUM |
| RF-002 | CRUD de CUM/FUM | Sí | `nomencladores` |
| RF-003 | CRUD de Municipios | Sí | `nomencladores` (14 precargados) |
| RF-004 | CRUD de Carreras | Decisión | `nomencladores` + `oferta`: catálogo global y oferta por entidad y año |
| RF-005 | CRUD de Áreas y Departamentos | Sí | `nomencladores` |
| RF-006 | CRUD de Cargos | Sí | `nomencladores` |
| RF-007 | Máximo de carreras por aspirante | Sí | `configuracion` (Parámetros) |
| RF-008 | Intentos de acceso y bloqueo | Sí | `configuracion`, `users/services/autenticacion.py` |
| RF-009 | SMTP con prueba de envío | Sí | `configuracion` (Correo) |
| RF-010 | Campos dinámicos de prematrícula | Sí | `prematricula` (`CampoPrematricula`) |
| RF-011 | Plantillas de correo editables | Sí | `configuracion` (Plantillas) |
| RF-012 | Autenticación con auth.uho.edu.cu | Parcial | `users/sgu.py`: adaptador listo y acceso local mientras tanto ([SGU.md](SGU.md)) |
| RF-013 | Registro de aspirantes con validación de correo | Sí | `users/services/registro.py` |
| RF-014 | Usuarios internos por entidad | Sí | `users` (Usuarios) |
| RF-015 | Una sola entidad por usuario | Sí | Restricción `usuario_una_sola_entidad` |
| RF-016 | Usuarios globales gestionados por el Superadmin | Sí | `users`, `roles` |
| RF-017 | Bloquear y desbloquear cuentas | Decisión | `users`: se desactivan; nunca se borran |
| RF-018 | Editar el perfil propio | Sí | `users` (`/auth/me/`); Mi perfil |
| RF-019 | Landing con carreras filtrables | Sí | `interes/views/publico.py`; `public/Inicio.jsx` |
| RF-020 | Detalle de carrera | Sí | `public/DetalleCarrera.jsx` |
| RF-021 | Expresión de interés anónima | Sí | `interes` |
| RF-022 | CI de 11 dígitos sin repetir | Decisión | `interes`: único por oferta (carrera + entidad + año) |
| RF-023 | Banner de convocatoria activa | Sí | `public/Inicio.jsx` |
| RF-024 | Listados públicos de otorgados | Parcial | `otorgamiento/publico.py`; `/resultados`. La consulta es por CI completo y el CI se muestra enmascarado. El listado está ordenado por apellidos, pero **no hay buscador por nombre** |
| RF-025 | Sección institucional | Parcial | Textos provisionales ([ANOTACIONES.md](ANOTACIONES.md) §4) |
| RF-026 | Convocatoria de interés anual | Sí | `interes` |
| RF-027 | La CI asigna carreras a entidades | Sí | `interes` (Oferta) |
| RF-028 | La entidad agrega carreras | Sí | `interes` (Oferta) |
| RF-029 | Dashboard de interés | Decisión | Interés → Dashboard. El pastel se sustituyó por barras ordenadas y el mapa es provisional |
| RF-030 | Dashboard global y local | Sí | Ámbito en `core/ambito.py` |
| RF-031 | Exportar interesados a Excel | Sí | `interes` (`exportar`) |
| RF-032 | Crear el plan de plazas | Sí | `plan_plazas` |
| RF-033 | Enviar el plan a las entidades | Sí | `plan_plazas` |
| RF-034 | Respuesta de cada entidad | Sí | `plan_plazas` |
| RF-035 | La CI fija la versión final | Decisión | `plan_plazas`: la CI fija el valor final de cada línea, sin rondas de negociación |
| RF-036 | Aprobación del Vicerrector | Decisión | Su aprobación publica. Lleva sello visible con usuario, fecha y hora, no firma criptográfica |
| RF-037 | Plan en PDF y Excel | Sí | `plan_plazas` (PDF con membrete y sello) |
| RF-038 | Historial del plan | Sí | `plan_plazas` (`HistorialPlan`) |
| RF-039 | Versión complementaria | Sí | `plan_plazas` |
| RF-040 | Convocatoria de solicitud | Sí | `convocatorias` |
| RF-041 | Aviso a los interesados | Sí | `convocatorias/tasks.py` (solo al abrir la 1.ª convocatoria del año) |
| RF-042 | Banner de la convocatoria de solicitud | Sí | `public/Inicio.jsx` |
| RF-043 | Cierre automático | Sí | Tarea Celery cada hora |
| RF-044 | Registro con CI único | Sí | `users` |
| RF-045 | Activación en 48 h | Sí | `users/tasks.py` |
| RF-046 | Perfil completo antes de elegir carreras | Sí | `aspirantes`; Mi perfil de aspirante |
| RF-047 | Hasta N carreras por prioridad, con arrastrar y soltar | Sí | `solicitudes`; `ListaOrdenable` (también con teclado) |
| RF-048 | Carrera asociada a una entidad | Sí | `solicitudes` (`OfertaCarrera`) |
| RF-049 | Reglas Facultad / CUM-FUM | Decisión | `solicitudes/services.py`: sin municipio del aspirante; se valida por tipo de entidad |
| RF-050 | Editar con la convocatoria abierta | Sí | `solicitudes` |
| RF-051 | Estado visible de la solicitud | Decisión | Se añaden los estados *Borrador* y *Observada* |
| RF-052 | Listado de solicitudes con filtros | Sí | `solicitudes/consultas.py`; Solicitudes |
| RF-053 | Estadísticas en tiempo real | Sí | Termómetro, distribución y evolución, actualizados cada 60 s |
| RF-054 | Detalle con visor e historial | Sí | `solicitudes` (`EventoHistorial`); visor de PDF e imagen |
| RF-055 | Observaciones y correcciones | Sí | `solicitudes/revision.py` |
| RF-056 | Exportar solicitudes | Sí | Excel y PDF con filtros |
| RF-057 | Ranking al cierre | Decisión | `otorgamiento`: ranking global por índice validado |
| RF-058 | Otorgamiento automático | Decisión | Lo genera la Secretaría General, una vez por convocatoria |
| RF-059 | Otorgamiento manual con justificación | Decisión | Ajustes del Jefe CI y del Vicerrector, con cascada |
| RF-060 | Aviso a los otorgados | Sí | Plantilla `plaza_otorgada` |
| RF-061 | Aviso a los no seleccionados | Sí | Dos plantillas, según haya o no segunda convocatoria |
| RF-062 | Segunda convocatoria con plazas restantes | Sí | `otorgamiento.services.plazas_restantes` |
| RF-063 | Resultado en PDF, Excel y público | Sí | `otorgamiento`; `/resultados` |
| RF-064 | Bloqueo tras aprobar | Decisión | Bloqueado al publicar; se descartó la reversión |
| RF-065 | Formulario de prematrícula | Sí | `prematricula`; reutiliza el CI y la certificación del perfil |
| RF-066 | Campos adicionales de prematrícula | Sí | Configuración → Campos de prematrícula |
| RF-067 | Borrador hasta la fecha límite | Sí | `prematricula` |
| RF-068 | Panel con estados y faltantes | Sí | Prematrícula (añade el estado *Incompleta*) |
| RF-069 | Revisar, aprobar y pedir correcciones | Decisión | Revisión por documento; "rechazar" es pedir correcciones y no hace perder la plaza |
| RF-070 | Alertas a 5 y 1 días del cierre | Sí | Tarea diaria `avisos_y_cierre_prematricula` |
| RF-071 | Filtro por documento faltante | Sí | `prematricula` (`falta_campo`, `falta_documento`) |
| RF-072 | Exportar prematrículas | Sí | Excel y PDF |
| RF-073 | Campana de notificaciones | Sí | `notificaciones`; `NotificationCenter` |
| RF-074 | Panel de notificaciones | Sí | Mis notificaciones (marcar como leída y eliminar) |
| RF-075 | Notificaciones automáticas | Parcial | Están todas menos la de **apertura de la convocatoria de interés**: no hay destinatarios registrados y se anuncia en la landing |
| RF-076 | Envíos masivos por grupo | Parcial | Grupos por rol, por entidad y todos los aspirantes. **Faltan** "aspirantes de una carrera" y "otorgados de una entidad" |

## Requisitos generales

| ID | Requisito | Estado | Dónde |
|---|---|---|---|
| RG-001 | UX centrado en el usuario | Parcial | Interfaz basada en el mockup aprobado y en los flujos de la ERS; no hubo estudio formal con usuarios |
| RG-002 | Interfaz intuitiva | Parcial | Pasos guiados, siguiente paso visible y alertas por rol; sin prueba con usuarios |
| RG-003 | Errores claros | Sí | Formato único de error en español (`core/exceptions.py`) |
| RG-004 | Retroalimentación inmediata | Sí | Indicadores de carga, avisos y confirmaciones |
| RG-005 | WCAG 2.1 AA | Parcial | Etiquetas, foco en los modales, avisos para lectores de pantalla, contraste comprobado y tablas alternativas a los gráficos; **sin auditoría formal** |
| RG-006 | HTTPS / TLS 1.2+ | Documentado | nginx con TLS y `prod.py` con cookies seguras (DESPLIEGUE §2.5) |
| RG-007 | Contraseñas con hash y sal | Sí | Argon2 |
| RG-008 | OWASP Top 10 | Parcial | ORM, escapado de React, CSRF, cookie `SameSite=Strict`, ámbito por objeto y `check --deploy`; **sin prueba de penetración** |
| RG-009 | Límite de intentos | Sí | 5 intentos / 15 minutos, configurable |
| RG-010 | Log de auditoría | Sí | `auditoria` |
| RG-011 | Sesión de 8 h de inactividad | Sí | Token de renovación JWT y control de actividad en el frontend |
| RG-012 | Validación y almacenamiento seguro de archivos | Sí | Validación por contenido, límites de tamaño y almacenamiento privado fuera del directorio web |
| RG-013 | Copias diarias, 30 días | Documentado | DESPLIEGUE §5 |
| RG-014 | Integración con SIGENU | **No** | Sin acceso al sistema: el índice lo valida a mano la entidad (`indice_validado`) |
| RG-015 | Integración con ASSET | **No** | Sin acceso al sistema: el centro de trabajo es texto libre |
| RG-016 | REST, JSON, `/api/v1/`, OpenAPI | Sí | `/api/docs/` |
| RG-017 | OAuth 2.0, JWT, ISO 8601, UTF-8 | Parcial | JWT, ISO 8601 y UTF-8 sí; OAuth 2.0 llegará con la conexión al SGU |
| RG-018 | Convenciones y comentarios | Sí | oxlint en el frontend; backend con PEP 8 (sin linter automático) |
| RG-019 | Repositorio con ramas y commits atómicos | Sí | [GIT.md](GIT.md) |
| RG-020 | Pruebas, cobertura ≥ 70 % | Sí | Backend 96 % |
| RG-021 | Contenedor Docker | Decisión | Solo documentado ([DOCKER.md](DOCKER.md)) |
| RG-022 | Documentación técnica y diagrama | Sí | README, DESARROLLO, DESPLIEGUE, [ARQUITECTURA.md](ARQUITECTURA.md) |
| RG-023 | Respuesta < 2 s con 100 usuarios | No verificado | Hay paginación y consultas optimizadas; falta una prueba de carga |
| RG-024 | Legislación de protección de datos | Parcial | Cifrado, ámbito, auditoría, consentimiento y retención; la validación jurídica corresponde a la UHO |
| RG-025 | Cifrado AES-256 de CI, celular y correo | Sí | `core/fields.py`, `core/crypto.py` |
| RG-026 | Política de privacidad y consentimiento | Parcial | Consentimiento explícito en el registro; falta el texto oficial (ANOTACIONES §3) |
| RG-027 | Acceso por rol y ámbito, con registro | Sí | `core/ambito.py` y auditoría de lecturas sensibles |
| RG-028 | Retención y anonimización | Sí | `retencion` (2 y 5 años, configurables) |

## Requisitos específicos

| ID | Requisito | Estado | Dónde |
|---|---|---|---|
| RE-001 | Identidad visual de la UHO | Parcial | Colores configurables desde la base de datos; faltan el escudo y el manual de identidad (ANOTACIONES §2 y §6) |
| RE-002 | SGU como proveedor de identidad | Parcial | Adaptador y documentación ([SGU.md](SGU.md)) |
| RE-003 | Diseño responsive | Sí | CSS Modules con puntos de corte para móvil, tableta y escritorio |
| RE-004 | API documentada | Sí | `/api/docs/` |
| RE-005 | Nomencladores como CRUD | Sí | `nomencladores` |
| RE-006 | Roles y permisos granulares | Sí | `roles`: matriz módulo × acción editable |
| RE-007 | docker-compose y `.env` | Decisión | `.env` con python-dotenv; Docker solo documentado |
| RE-008 | Versionado con commits regulares | Sí | GitHub, rama `develop` |
| RE-009 | Membrete en los PDF | Sí | `core/templates/pdf/base.html` (el escudo aparece cuando se carga) |
| RE-010 | SMTP editable desde el panel | Sí | `configuracion` |

## Requisitos no funcionales

| ID | Requisito | Estado | Dónde |
|---|---|---|---|
| RNF-001 | 500 usuarios concurrentes, < 3 s | No verificado | Requiere una prueba de carga |
| RNF-002 | Landing en < 2 s | Parcial | Build minificado, gzip en nginx, imágenes con carga diferida; sin medir |
| RNF-003 | Disponibilidad del 99 % | No verificado | Depende de la infraestructura; los servicios systemd se reinician solos |
| RNF-004 | Copias diarias, RTO ≤ 4 h | Documentado | DESPLIEGUE §5 |
| RNF-005 | 5 MB por archivo y 20 MB por aspirante | Sí | `aspirantes`, `prematricula` (cuotas separadas) |
| RNF-006 | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+ | Parcial | `vite.config.js` no fija `build.target`, así que se usa el objetivo por defecto de Vite, que exige navegadores más recientes |
| RNF-007 | Arquitectura en capas | Sí | Vistas → services → modelos ([ARQUITECTURA.md](ARQUITECTURA.md)) |
| RNF-008 | Logs con rotación diaria, 90 días | Sí | `LOGGING` en `settings/base.py` |
| RNF-009 | `/api/v1/` y Swagger en `/api/docs` | Sí | `config/urls.py` |
| RNF-010 | Despliegue Linux con Docker | Decisión | Despliegue en Linux sin Docker documentado; Docker en DOCKER.md |
