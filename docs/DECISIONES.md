# Decisiones del cliente

La ERS (sección 1.1) establece que cualquier discrepancia con la implementación
se resuelve a favor del documento, **salvo decisión documentada del cliente**.
Este archivo registra esas decisiones.

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

## Solicitud de carrera

| Tema | Decisión |
|---|---|
| Índice académico | Escala de 0 a 100. |
| Municipio del aspirante (RF-049) | El aspirante no tiene municipio asociado. Puede elegir carreras de varias Facultades y de varios CUM/FUM, pero no la misma carrera en dos CUM/FUM distintos. Sí puede elegir la misma carrera en un CUM/FUM y en una Facultad. |

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
| Segunda convocatoria (RF-062) | Los no seleccionados pueden volver a solicitar. Plazas restantes = plan − otorgadas. |

## Prematrícula

| Tema | Decisión |
|---|---|
| Renuncia | No existe: la ERS no contempla que el aspirante rechace la plaza ni describe la matrícula definitiva. |
| "Rechazar" (RF-069) | Significa que el aspirante debe corregir o reenviar sus documentos. **No pierde la plaza.** |

## Plan de plazas

| Tema | Decisión |
|---|---|
| Estados (RF-032 a 039) | Se siguen los 7 estados de la ERS, no los 6 pasos del mockup. |
