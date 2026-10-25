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

## Expresión de interés

| Tema | Decisión |
|---|---|
| Email (RF-021) | Obligatorio (el mockup lo marcaba opcional). Es la única vía para avisar a los interesados de la convocatoria (RF-041), porque no tienen cuenta. |

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
