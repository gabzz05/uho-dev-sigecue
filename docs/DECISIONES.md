# Decisiones del cliente

La ERS (sección 1.1) establece que cualquier discrepancia con la implementación
se resuelve a favor del documento, **salvo decisión documentada del cliente**.
Este archivo registra esas decisiones. El estado de cada requisito está en
[TRAZABILIDAD.md](TRAZABILIDAD.md).

## Resumen: desviaciones principales respecto a la ERS

| Tema | ERS | Implementado | Motivo |
|---|---|---|---|
| Plazas por aspirante | No lo limita | **Una sola plaza**, la de mayor prioridad que alcance | Decisión del cliente |
| Regla 5 del algoritmo | Prioriza el CUM/FUM del municipio sobre la Facultad | **Descartada**: manda la prioridad del aspirante | Manda la prioridad elegida por el aspirante |
| Orden del ranking | Por carrera y entidad | **Global**, por índice validado, luego confirmación y luego id | Consecuencia de dar una sola plaza por aspirante |
| Índice | Declarado | Solo cuenta el **validado** por una entidad | El índice es un dato único del aspirante, no de cada entidad |
| Misma carrera (RF-049) | En un CUM/FUM "de su municipio" | Permitida en **una Facultad y un CUM/FUM**, nunca en dos del mismo tipo | El aspirante no tiene municipio asociado |
| Estado *Observada* | No existe | Nuevo estado, con observaciones corregibles que excluyen del ranking hasta resolverse | Una solicitud observada no es lo mismo que una en revisión |
| Otorgamiento (RF-058, RF-059) | Admin o secretario de la entidad | Lo genera la **Secretaría General**; ajustan el **Jefe CI** y el **Vicerrector**; la aprobación del Vicerrector publica | Decisión del cliente |
| Reversión tras aprobar (RF-064) | Permitida con justificación | **Descartada**: publicado, no cambia | Decisión del cliente |
| Firma del Vicerrector (RF-036, RF-037) | Firma digital | **Sello visible** con usuario, fecha y hora | Decisión del cliente |
| Resultado público (RF-024) | Listados con nombre o CI | Solo otorgados, **CI enmascarado**, sin índice, posición ni prioridad; consulta individual por CI completo | Minimización de datos |
| Pastel por entidad (RF-029) | Gráfico de pastel | **Barras horizontales** ordenadas | Más legible con muchas entidades |
| Mapa (RF-029) | Por municipio | **Provisional** de casillas, por municipio de la entidad ofertante | Falta la geometría oficial |
| "Rechazar" la prematrícula (RF-069) | Rechazar | **Pedir correcciones**: nunca hace perder la plaza | No existe la renuncia |
| Retención (RG-028) | 2 años recomendados | **Configurable**: 2 años (no seleccionados) y 5 (otorgados); anonimizar en lugar de borrar | Reclamaciones tardías y consultas sobre los otorgados; estadísticas |
| Usuarios (RF-017) | Bloquear | Se **desactivan**, nunca se borran | Decisión del cliente |
| Docker (RG-021, RE-007) | Entrega en Docker | **Solo documentado** | Decisión del cliente |

## Infraestructura

| Tema | Decisión |
|---|---|
| Docker (RG-021, RE-007) | Se pospone. Ver [DOCKER.md](DOCKER.md). |
| Tareas programadas | Celery + Redis. |
| Notificaciones en tiempo real | Polling (sin WebSockets). |
| Almacenamiento de archivos | Disco local, fuera del directorio web público. |
| Autenticación interna (RE-002, RF-012) | Se deja un adaptador para el SGU (`auth.uho.edu.cu`) y login local mientras tanto. |
| Identidad visual (RE-001) | Paleta del mockup (`#1A3A6B`, `#C8102E`) como valor por defecto. Los colores se guardan en base de datos y el frontend los aplica en tiempo de ejecución. |

## Datos personales

| Tema | Decisión |
|---|---|
| Cifrado (RG-025) | CI, celular y email se cifran en reposo con AES-256. El CI guarda además un hash para comprobar unicidad y buscar. |
| Listado público de otorgados (RF-024) | Se puede buscar por nombre o CI, pero el listado **no muestra el CI completo**: solo nombre, carrera y entidad (o CI enmascarado). Así se cumplen RF-024, RG-025 y RG-027. |

## Autenticación y usuarios

| Tema | Decisión |
|---|---|
| Login | Aspirantes con su email; usuarios internos con nombre de usuario y contraseña local hasta que se conecte el SGU. |
| Sesión (RG-011) | Access token de 15 min en memoria del navegador y refresh en cookie httpOnly; la sesión caduca tras 8 h de inactividad o al cerrarla. |
| Roles (RE-006) | Los 13 roles de la ERS vienen precargados con una matriz de permisos inicial. El Superadmin puede editar permisos y crear roles nuevos. |
| Auditoría (RG-010) | Las lecturas (GET) no se auditan automáticamente; las lecturas sensibles se registran explícitamente en cada módulo. |
| Borrado de usuarios (RF-014) | Los usuarios no se borran, para conservar la trazabilidad. Se desactivan (`bloquear`) y se reactivan (`desbloquear`). No existe el permiso `usuarios.eliminar`. |
| Perfil (RF-018) | El usuario edita su celular, su foto y su contraseña. El email no es editable por ahora (cambiarlo exigiría volver a verificarlo). |
| Celular | 8 dígitos empezando por 5 (`^5\d{7}$`). |

## Nomencladores

| Tema | Decisión |
|---|---|
| Carreras (RF-004) | Catálogo global sin entidad. La entidad que la oferta cada año se define en `OfertaCarrera` (carrera + entidad + año), como en el modelo conceptual. Así una misma carrera puede estar en una Facultad y en varios CUM/FUM (RF-049). |
| Modalidad | Un único valor: "Por encuentro". Se amplía si aparece otra modalidad. |
| Áreas y departamentos (RF-005) | El departamento pertenece a un área; el área, a una Facultad o a un CUM/FUM. El Jefe de Área se vincula a un área concreta. |
| Cargos (RF-006) | El usuario interno tiene un cargo opcional. |
| Municipios (RF-003) | Se precargan los 14 municipios de la provincia de Holguín. |
| Usuario–entidad | Dos claves foráneas (`facultad`, `cum_fum`) con restricción de base de datos, en lugar de `tipo_entidad` + `entidad_id`. |
| Imágenes | Las de carreras, facultades y CUM/FUM son públicas (las sirve nginx). Los documentos de los aspirantes son privados y solo los entrega la API. |
| Escritura de catálogos | Municipios, facultades, CUM/FUM, cargos y carreras los modifican solo los roles globales. Áreas y departamentos los gestiona también cada entidad. |

## Configuración del sistema

| Tema | Decisión |
|---|---|
| Quién la modifica | Solo el Superadmin. Los demás, con `configuracion.ver`, la ven en modo lectura. |
| Contraseña SMTP (RE-010) | Cifrada con AES-256 (reversible, porque se usa para autenticarse). La API nunca la devuelve. |
| SMTP: panel o `.env` | Manda la configuración del panel si está activada; si no, la del `.env`. |
| Plantillas (RF-011) | Texto plano con variables `{{ variable }}`, sin HTML. Se muestran las variables disponibles. El correo de activación también es una plantilla. |
| Identidad visual | Nombre de la institución, color primario, primario claro, acento y escudo. |
| Parámetros RF-007 / RF-008 | En base de datos; los valores iniciales salen del `.env`. |
| Campos dinámicos de prematrícula (RF-010) | Se implementan en el feature de prematrícula, no en configuración. |

## Notificaciones

| Tema | Decisión |
|---|---|
| Polling (RF-073) | Cada 60 s y solo con la pestaña visible. |
| Contenido in-app | El mismo de la plantilla de correo: asunto como título y cuerpo como texto (recortado como resumen en la lista). |
| Grupos masivos (RF-076) | Por ahora: por rol, por entidad y todos los aspirantes. Por carrera y por otorgamiento llegarán con esos módulos. |
| Alcance | Quien tenga `notificaciones.crear`. Los roles locales solo dentro de su entidad; "todos los aspirantes" es solo para roles globales (los aspirantes no pertenecen a una entidad hasta que solicitan). |
| Correo en masivos | Opcional, desmarcado por defecto. Las automáticas siempre van por los dos canales. |
| Limpieza | Las notificaciones se conservan; el usuario puede borrarlas. Sin borrado automático. |

## Expresión de interés

| Tema | Decisión |
|---|---|
| Email (RF-021) | Obligatorio (el mockup lo marcaba opcional). Es la única vía para avisar a los interesados de la convocatoria (RF-041), porque no tienen cuenta. |
| Alcance del feature | Convocatoria, oferta, landing, expresión de interés, listado y Excel juntos. El dashboard con gráficos y mapa (RF-029/030) va en el feature de dashboard. |
| Convocatoria (RF-026) | Una por año académico (`2026-2027`). Estados borrador, abierta y cerrada. Apertura manual y cierre automático por fecha. Solo una abierta a la vez. |
| Oferta (RF-027/028) | La CI asigna carreras a cualquier entidad. Cada entidad agrega carreras del catálogo a la suya, sin un permiso aparte, y no puede quitar lo asignado por la CI. |
| Sin convocatoria abierta | La landing muestra el catálogo de carreras sin el botón "Me interesa". |
| Duplicados (RF-022) | El mismo CI no repite el interés por la misma oferta (carrera + entidad + año). |
| Contador de interesados | No se muestra en la landing: podría influir artificialmente en la decisión de los aspirantes. |
| Confirmación | Se envía un correo al registrar el interés (plantilla `interes_confirmado`). |
| Sección institucional (RF-025) | Textos provisionales, sin edición desde el panel por ahora. |
| Antispam | Límite de envíos por IP, sin captcha. |
| Exportaciones | Se auditan siempre, especialmente cuando incluyen CI, email o celular. El Excel se hizo en este feature y el PDF irá con el Plan de Plazas. |

## Convocatoria de solicitud

| Tema | Decisión |
|---|---|
| Requisito para abrir | Plan de plazas publicado del mismo año académico. |
| Entidades (RF-040) | Lista opcional; vacía = todas las entidades con plazas en el plan. |
| Aviso a interesados (RF-041) | A los de la convocatoria de interés del mismo año académico: un correo por persona e in-app si ya tiene cuenta. Solo al abrir la primera convocatoria del año. |
| Apertura y cierre | Apertura manual, cierre automático por fecha, una sola abierta a la vez. |
| Número de convocatoria (RF-062) | Existe desde ahora; la validación contra el otorgamiento de la anterior se hace en ese feature. |
| Landing | Muestra los dos avisos (solicitud e interés) si coinciden; el de solicitud tiene prioridad visual. |

## Solicitud de carrera

| Tema | Decisión |
|---|---|
| Índice académico | Escala de 0 a 100. Lo declara el aspirante (`indice_declarado`); la entidad lo valida contra la certificación (`indice_validado`). |
| Municipio del aspirante (RF-049) | El aspirante no tiene municipio asociado. Puede elegir carreras de varias Facultades y de varios CUM/FUM, pero no la misma carrera en dos CUM/FUM distintos. Sí puede elegir la misma carrera en un CUM/FUM y en una Facultad. La regla se aplica por tipo de entidad (tampoco en dos Facultades). |
| Número de carreras (RF-047) | Mínimo 1; máximo, el parámetro global `max_carreras_aspirante` (5 por defecto). |
| Documentos (RF-046) | Catálogo dinámico de tipos de documento que gestiona el Superadmin. Semillas: CI anverso, CI reverso y certificación de estudios. PDF, JPG o PNG. |
| Límites (RNF-005) | 5 MB por archivo y 20 MB por aspirante, contando los archivos vigentes (documentos y foto). |
| Versiones de documentos | Sustituir un documento crea una versión nueva y la última es la vigente. Las anteriores se conservan como evidencia hasta la política de retención, con un máximo de 10 por documento (al superarlo se borra la más antigua, para que el aspirante nunca quede bloqueado). El aspirante y las entidades ven solo la vigente; los roles globales, el historial. |
| Foto de perfil | La de la cuenta (`Usuario.foto`), JPG o PNG, en el almacenamiento privado, sin versiones. |
| Perfil completo | Datos personales, correo validado, foto, centro de trabajo, índice declarado, documentos obligatorios, al menos una carrera y privacidad aceptada. Se calcula siempre a partir del estado real; el campo guardado es solo una caché. |
| Confirmación | La solicitud empieza en borrador y se confirma de forma explícita (pasa a Pendiente). Solo la primera confirmación envía el correo y la notificación con el resumen; los cambios posteriores no notifican y se ven en la fecha de última modificación. Al cerrar la convocatoria se congela la última versión. |
| Fechas de la solicitud | Tres fechas distintas: creación del borrador, confirmación oficial y última modificación. |
| Edición | Mientras la convocatoria esté abierta, el aspirante puede cambiar datos, índice, documentos, carreras y prioridades. Al cerrar, solo lectura. |
| Descarga de documentos | Permiso `solicitudes.documentos_descargar` **y** que la entidad participe en alguna carrera de una solicitud confirmada del aspirante (los roles globales, siempre). Por semilla: roles globales, Secretario(a) de Facultad y de CUM/FUM, Director(a) de CUM/FUM. No: Jefes de Área, Vicedecanos, Admins ni roles de consulta. |
| Motivo de descarga | Automático, sin pedirlo al usuario: `consulta_documentacion` (el propio aspirante) o `revision_solicitud` (personal). Se audita junto con usuario, fecha, IP y archivo. |

## Gestión de solicitudes

| Tema | Decisión |
|---|---|
| Qué ve una entidad (RF-052) | Datos personales, índice, documentos, observaciones y **solo sus opciones**. No ve carreras ni prioridades de otras entidades (minimización de datos). |
| Permisos | Observar y validar el índice: `solicitudes.editar` (secretarías y admins de entidad, y roles globales). Abrir documentos: `solicitudes.documentos_descargar`, aparte. El Director(a) de CUM/FUM ve y descarga, pero no revisa. |
| Estado *Observada* | Estado propio de la solicitud: Pendiente → En revisión → Observada → corrección del aspirante → Pendiente. |
| Paso a *En revisión* | Automático con la primera acción de revisión: validar índice, crear, resolver o reabrir una observación. Sin botón manual ni estado "documentación revisada". |
| Qué se observa | Solo elementos corregibles por el aspirante: un documento, el índice, el centro de trabajo o la foto. CI, nombre y correo: soporte administrativo. |
| Ciclo de la observación | Abierta → Corregida (el aspirante) → Resuelta o Reabierta (la entidad). |
| Ranking | Toda observación no resuelta (abierta, corregida, reabierta) excluye la solicitud **completa**. Una regla única, sin lógica especial en el otorgamiento. |
| `afecta_elegibilidad` | No cambia la regla del ranking. Si es verdadero: anula el índice validado, exige validarlo de nuevo y marca la revisión documental como pendiente. Por defecto verdadero para el índice y la certificación de estudios; falso para CI, foto y centro de trabajo. La entidad puede cambiarlo al observar. |
| Corrección tras el cierre | Permitida, con desbloqueo selectivo de lo observado. Nunca se añaden, quitan ni reordenan carreras. |
| Índice validado | Obligatorio para el ranking: sin validar no participa (el declarado no cuenta). Una sola entidad lo valida; después solo un rol global lo cambia. Se anula si el aspirante cambia el declarado o por una observación que afecta la elegibilidad. Después lo puede validar cualquier entidad con acceso a la solicitud. |
| Observaciones de otras entidades | Todas las entidades las ven, con su autora. Cada una gestiona solo las suyas; los roles globales, cualquiera. |
| Estadísticas (RF-053) | SVG y CSS propios, sin librerías de gráficos. Polling cada 60 s, como las notificaciones. |
| Historial (RF-054) | Selección (antes/después, al guardar), documentos (versión anterior y nueva), datos del perfil, índice y ciclo de las observaciones, con usuario y fecha. |

## Otorgamiento (sección 5.9)

| Tema | Decisión |
|---|---|
| Plazas por aspirante | Cada aspirante recibe **una sola plaza**: la de mayor prioridad (según su propio orden) que alcance. |
| Orden de asignación | Se recorre a todos los aspirantes de mayor a menor índice académico (empates por fecha y hora de solicitud) y cada uno toma su opción de mayor prioridad que tenga plaza libre. |
| Regla 5 del algoritmo (CUM antes que Facultad) | **Se descarta.** Manda la prioridad elegida por el aspirante. |
| Alcance | El otorgamiento automático es **global** (todas las entidades a la vez). Se ejecuta **una vez por convocatoria**, con un botón; no se puede volver a ejecutar. Lo lanza la **Secretaria General**. |
| Quién edita (RF-058/059) | **Solo el Jefe de la Comisión de Ingreso y el Vicerrector de Formación.** Las Facultades y CUM/FUM solo consultan el otorgamiento de su entidad. |
| Ediciones manuales | Requieren justificación. Al "aplicar cambios" el sistema resuelve las cascadas: si se otorga a un aspirante una opción de mayor prioridad, pierde la que tenía, y las vacantes que queden las cubre el algoritmo automático. Nunca se pueden otorgar más plazas que las del plan. |
| Quién entra en el ranking | Quedan fuera los aspirantes con perfil incompleto o con observaciones pendientes. |
| Flujo | Ranking generado (al cerrar la convocatoria) → otorgamiento automático → revisión y aprobación del Jefe CI → revisión y aprobación del Vicerrector, que **publica**. El Vicerrector no devuelve al Jefe CI: edita y aprueba. |
| Publicación | Todo junto, no por entidad. Al publicar se notifica a otorgados y no seleccionados, se publica el listado y se habilita la prematrícula. |
| Cambios después de publicar (RF-064) | **No hay.** Se descarta la reversión con justificación. |
| Segunda convocatoria (RF-062) | Los no seleccionados pueden volver a solicitar. Plazas restantes = plan − otorgadas. Solo se crea con la anterior cerrada y su otorgamiento publicado. Al publicar, el Vicerrector indica si habrá segunda convocatoria, y eso cambia el aviso a los no seleccionados. |
| Generación | La Secretaria General ve antes un resumen (elegibles, no elegibles y motivos) y confirma. Al ranking entran solo los elegibles; los demás quedan fuera. |
| Desempate | Índice validado, luego `confirmada_at` (la solicitud oficial nace al confirmarse) y, por último, el id. |
| Ajustes manuales | Solo a aspirantes elegibles y solo en carreras que solicitaron. Otorgar fija una opción; quitar la impide. Tras cada ajuste el reparto se recalcula (primero los ajustes, después el algoritmo cubre las vacantes por ranking). Se pueden anular con justificación. |
| Permisos por etapa | `otorgamiento.generar` (Secretaría General), `otorgamiento.aprobar` (Jefe CI: revisa, ajusta y aprueba) y `otorgamiento.publicar` (Vicerrector: revisa, ajusta y publica). Desaparece `otorgamiento.editar`. |
| Visibilidad del provisional | Solo los roles globales. El aspirante no ve resultados intermedios; las entidades ven lo suyo tras publicar. |
| Snapshot | Obligatorio: `ResultadoOtorgamiento` guarda índice utilizado, posición, motivo de exclusión, opciones y lo otorgado. Queda congelado al publicar. |
| Revisión tras generar | Generado el otorgamiento, la revisión de esa convocatoria (validar, observar, corregir) se cierra, para que el snapshot no quede desfasado. |

## Retención de datos (RG-028)

| Tema | Decisión |
|---|---|
| Plazos | `retencion_anios` = 2 (no seleccionados, expresiones de interés y versiones antiguas) y `retencion_otorgados_anios` = 5 (otorgados: reclamaciones tardías, prematrícula, consultas). Los configura el Superadmin. |
| Desde cuándo | Publicación del último otorgamiento del año académico. Con una solicitud o participación posterior, no se anonimiza todavía. |
| Sin solicitud confirmada | Plazo base desde el último acceso (o el registro): no hay otorgamiento del que contar. |
| Anonimizar, no borrar | Se quitan nombre y apellidos, CI, correo, celular, centro de trabajo, foto, documentos con todas sus versiones y notificaciones; la cuenta se desactiva. Se conservan solicitudes, carreras, prioridades, estados, resultado, índice, estadísticas y snapshots. |
| Nombre anonimizado | "Aspirante anonimizado", sin número: un `#id` seguiría siendo un identificador. La clave técnica queda solo en la base de datos. |
| Versiones de documentos | Las históricas se borran al vencer la retención; la vigente se conserva solo mientras el expediente siga sujeto a conservación. Al anonimizar se borran todas. |
| Expresiones de interés | Cierre de la convocatoria + retención: se anonimizan nombre, CI, correo y celular; se conservan carrera, entidad, municipio y fecha. |
| Auditoría | Excluida: la anonimización no altera los registros de auditoría. |
| Ejecución | Automática mensual y manual adelantada por el Superadmin, con vista previa (aspirantes, intereses, documentos, espacio). Cada ejecución en `RetencionEjecutada` y en la auditoría. |
| Copias de seguridad | No es retroactiva: con 30 días de retención de backups, los datos desaparecen de las copias en el ciclo siguiente. |

## Dashboards

| Tema | Decisión |
|---|---|
| Dónde (RF-029) | Dashboard de interés dentro del módulo de interés. Dashboard principal: vista ejecutiva por rol (interés, plan, solicitudes, otorgamiento, prematrícula) con totales, pendientes, alertas y accesos rápidos. |
| Gráfico por entidad | Barras horizontales ordenadas de mayor a menor en lugar del pastel de la ERS: es más legible con muchas entidades. |
| Mapa | Provisional mientras no llegue la geometría oficial: 14 casillas en posición aproximada, color por intensidad, cantidad visible y tabla complementaria. La interfaz admite cambiar la fuente visual. |
| Municipio | La distribución territorial se calcula por **municipio de la entidad ofertante**, no por el de la persona (la expresión de interés no lo guarda). |
| Ámbito (RF-030) | Globales: todo. Locales: solo su entidad. |
| Actualización | Polling cada 60 s con la pestaña visible. Sin WebSockets en esta fase. |
| Alertas operativas | Tarjetas de atención rápida en el dashboard principal (no notificaciones): convocatorias próximas a cerrar, solicitudes observadas o pendientes, otorgamiento pendiente de generar o aprobar, prematrículas por revisar, con correcciones o incompletas. |

## Resultados públicos

| Tema | Decisión |
|---|---|
| Qué se publica | Solo los otorgados: nombre y apellidos, CI enmascarado, carrera, entidad y convocatoria. No se publican no seleccionados, índice, posición, prioridad ni motivos. |
| CI | Enmascarado, con los 4 últimos dígitos visibles: `*******2345`. |
| Consulta individual | Por CI completo: convocatoria, resultado y, si aplica, carrera y entidad. Sin datos de terceros. Mismo límite por IP que la expresión de interés. |
| Respuesta sin resultado | Un único mensaje ("No existe un resultado publicado para los datos introducidos."), exista o no el CI, contra la enumeración de identidades. |
| Organización | Filtros por convocatoria, entidad y carrera. Primera y segunda convocatoria en listados separados. Orden: carrera, entidad, apellidos y nombre. |
| Vigencia | Visible en la landing hasta el cierre de la prematrícula. Después, solo para usuarios internos autorizados y sujeto a la retención de datos. |
| Descarga | No hay descarga pública: solo se ve en pantalla. |

## Prematrícula

| Tema | Decisión |
|---|---|
| Renuncia | No existe: la ERS no contempla que el aspirante rechace la plaza ni describe la matrícula definitiva. |
| "Rechazar" (RF-069) | Significa que el aspirante debe corregir o reenviar sus documentos. **No pierde la plaza.** |
| Período | Lo fija la Secretaría General (`prematricula.configurar`) por cada otorgamiento publicado: inicio y cierre. El cierre es también el último día del listado público. Aviso al abrir y recordatorios a 5 y 1 días del cierre. |
| Documentos del perfil | CI anverso, CI reverso y certificación se reutilizan (versión vigente). Solo se vuelven a pedir si la entidad los rechaza. |
| Foto tipo carné | Distinta de la foto de perfil: es un campo propio de la prematrícula, requerido. |
| Campos dinámicos (RF-010, RF-066) | `CampoPrematricula` (nombre, tipo texto/archivo/imagen, requerido, orden, activo), gestionado por el Superadmin. Semillas: foto tipo carné, carta de autorización del centro de trabajo, solicitud personal firmada. |
| Archivos | PDF, JPG o PNG (imágenes: JPG o PNG), 5 MB, con versiones. Cuota de 20 MB propia de la prematrícula, separada de la del perfil. |
| Estados | Pendiente, Borrador, Completada, Con correcciones, Aprobada e Incompleta (venció el plazo sin enviarla; no es renuncia). Revisión por documento; se aprueba cuando todos los requeridos están aprobados. Se guardan `fecha_aprobacion` y `aprobado_por`. |
| Quién revisa | Admin y Secretario de la entidad donde obtuvo la plaza, y roles globales (por semilla, Jefe CI y Secretaría General), con `prematricula.editar`. Descargar: `solicitudes.documentos_descargar`, limitado a esa entidad. |
| Correcciones tras el cierre | Permitidas, solo de lo rechazado (desbloqueo selectivo). |
| Avisos | `prematricula_abierta`, `prematricula_recordatorio`, `prematricula_correccion` y `prematricula_aprobada`, por correo e in-app, editables por el Superadmin. |

## Plan de plazas

| Tema | Decisión |
|---|---|
| Estados (RF-032 a 039) | Los 7 estados de la ERS se reparten en dos niveles. Plan: borrador, enviado, revisión de la CI, en aprobación y publicado. Cada entidad: pendiente, en revisión y propuesta enviada. "Aprobado" y "Publicado" son uno solo: **la aprobación del Vicerrector publica directamente**. |
| Plan y oferta | Cada línea apunta a una carrera + entidad. Al publicar, una carrera nueva aceptada crea su `OfertaCarrera`; una que sale del plan conserva la oferta (por el historial de interés) sin plazas. |
| Espera de las entidades | La CI puede esperar a que todas envíen su propuesta o forzar el paso. Las que no enviaron conservan la propuesta inicial. |
| Quién responde por la entidad | Admin, Vicedecano o Director. El Jefe de Área ve y comenta, pero no envía la propuesta. |
| Negociación (RF-035) | Sin rondas de ida y vuelta: la CI fija el valor final de cada línea con un comentario. Si no toca una línea, se acepta lo propuesto por la entidad. |
| Historial (RF-038) | Usuario, fecha, valor anterior, valor nuevo, comentario y número de versión. La versión sube con cada versión final generada. |
| Versión complementaria (RF-039) | Incluida: un plan nuevo que parte de los valores aprobados vigentes y recorre el flujo completo. |
| "Firma" del Vicerrector (RF-036/037) | Marca de aprobación visible (usuario, fecha y hora) en el PDF; no es una firma criptográfica. |
| PDF y Windows | WeasyPrint se mantiene. Sin las librerías nativas, las pruebas del PDF se saltan y la exportación avisa con un error claro. |
