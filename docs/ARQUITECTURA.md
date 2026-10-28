# Arquitectura de SIGECUE

Arquitectura real del sistema construido. El detalle de cada módulo está en
[README.md](README.md), y el porqué de cada decisión en
[DECISIONES.md](DECISIONES.md).

## Vista general

```
navegador ──► nginx ──┬──► frontend/dist (React compilado)
                      ├──► /media/ (imágenes públicas: carreras, entidades, escudo)
                      └──► /api/v1/ ──► gunicorn ──► Django + DRF ──► PostgreSQL
                                                        │
                                       Celery (worker + beat) ◄──► Redis
                                                        │
                                              MEDIA_ROOT (archivos privados)
```

- **Frontend:** SPA en React + Vite. Habla solo con la API.
- **Backend:** API REST en Django + Django REST Framework, versionada en
  `/api/v1/` y documentada con OpenAPI (`/api/docs/`).
- **Base de datos:** PostgreSQL en producción y SQLite en desarrollo.
- **Tareas en segundo plano:** Celery con Redis. En desarrollo se ejecutan en el
  mismo proceso (`CELERY_TASK_ALWAYS_EAGER`).
- **Despliegue:** Docker Compose con seis servicios (`db`, `redis`, `backend`,
  `worker`, `beat`, `web`), descritos en [DOCKER.md](DOCKER.md). También se
  puede instalar sin contenedores ([DESPLIEGUE.md](DESPLIEGUE.md)).

## Flujo de una petición

```
componente React ─► hook (useListado, useCarga, useFormulario…) ─► services/*.js (axios + token)
   ─► /api/v1/… ─► middleware de auditoría ─► vista DRF (permiso por módulo y ámbito)
   ─► serializer (validación de formato) ─► services.py (reglas de negocio, transacción)
   ─► modelos / ORM ─► PostgreSQL
```

- **Vistas:** son delgadas. Comprueban permisos, validan con el serializer,
  llaman al service y devuelven la respuesta.
- **Reglas de negocio:** viven en `services.py`. Ejemplos: transiciones de
  estado, límites, elegibilidad o el reparto de plazas. Las transiciones releen
  la fila con `select_for_update` para que dos peticiones simultáneas no se
  pisen.
- **Errores:** un único formato, `{"error": {"codigo", "mensaje", "detalles"}}`.
  Los services lanzan `ErrorDeNegocio` con un mensaje en español para el
  usuario.

## Apps del backend

| App | Responsabilidad |
|---|---|
| `core` | Cifrado de campos, ámbito de datos, errores, paginación, almacenamiento, exportación a Excel y PDF |
| `roles` | Catálogo de permisos módulo × acción, roles y comprobación de permisos |
| `users` | Usuarios, autenticación JWT, registro y activación de aspirantes, adaptador SGU |
| `auditoria` | Log de auditoría inmutable: middleware para toda escritura y registro explícito de lecturas sensibles |
| `nomencladores` | Facultades, CUM/FUM, municipios, carreras, áreas, departamentos y cargos |
| `configuracion` | Parámetros, SMTP, identidad visual y plantillas de correo |
| `notificaciones` | Notificaciones in-app con su correo y envíos masivos |
| `oferta` | Oferta de carrera: carrera + entidad + año, con las plazas del plan |
| `interes` | Convocatoria de interés, expresiones de interés, landing y su dashboard |
| `plan_plazas` | Plan de plazas: flujo multinivel, historial, versión complementaria y PDF |
| `convocatorias` | Convocatorias de solicitud (1.ª, 2.ª…) y aviso a interesados |
| `aspirantes` | Perfil del aspirante, tipos de documento y documentos versionados con descarga controlada |
| `solicitudes` | Solicitud de carreras, revisión de las entidades, observaciones, historial y estadísticas |
| `otorgamiento` | Ranking, reparto de plazas (función pura), ajustes, aprobación, publicación, snapshot y resultados públicos |
| `prematricula` | Período, expediente con revisión por documento, correcciones y aprobación |
| `dashboard` | Vista ejecutiva por rol con alertas operativas |
| `retencion` | Política de retención: anonimización y registro de ejecuciones |

## Seguridad y datos personales

- **Autenticación:**
  - token de acceso JWT de 15 minutos, guardado solo en memoria;
  - token de renovación en una cookie `httpOnly`, que rota en cada uso y se
    invalida al cerrar sesión;
  - la sesión caduca tras 8 horas sin actividad;
  - contraseñas con hash Argon2.
- **Autorización:**
  - **permiso:** cada vista declara su módulo (`PermisoModulo`), y una acción
    no declarada se deniega;
  - **ámbito:** los roles globales ven todo y los locales solo su Facultad o
    CUM/FUM (`core/ambito.py`).
- **Cifrado en reposo** (AES-256-GCM): CI, correo y celular, con un hash HMAC
  al lado para buscar y comprobar unicidad sin descifrar.
- **Auditoría:** el log es inmutable para la API, el panel de administración y
  el ORM. Registra toda escritura en la API, además de las descargas de
  documentos, el detalle de solicitudes y las exportaciones. La retención de
  datos no lo toca.

## Archivos

| Almacenamiento | Contenido | Quién lo sirve |
|---|---|---|
| Privado (`MEDIA_ROOT`) | Foto, documentos del perfil y archivos de prematrícula | Solo la API, con permiso y ámbito; cada descarga se audita |
| Público (`PUBLIC_MEDIA_ROOT`) | Imágenes de carreras, entidades y escudo | nginx en `/media/` |

- Los documentos se validan **por contenido**, no por la extensión: PDF, JPG o
  PNG, de 5 MB como máximo.
- Cada sustitución crea una versión nueva; se guardan como máximo 10.
- Cuotas de 20 MB por aspirante: una para el perfil y otra aparte para la
  prematrícula.
- El frontend pide los archivos privados con el token y los muestra como
  `blob:` (`useArchivoPrivado`).

## Exportaciones

- **Excel:** `core/excel.py` (`respuesta_excel`, con openpyxl).
- **PDF:** `core/pdf.py` (`respuesta_pdf`, con WeasyPrint y membrete
  institucional). WeasyPrint se importa solo al usarse: si faltan sus
  librerías nativas, únicamente falla la exportación a PDF, con un mensaje
  claro.
- Toda exportación con datos personales se audita.

## Tareas programadas (Celery beat)

| Tarea | Cuándo | Qué hace |
|---|---|---|
| `users.eliminar_cuentas_no_verificadas` | Cada hora | Borra las cuentas sin activar pasadas 48 h (RF-045) |
| `interes.cerrar_convocatorias_vencidas` | Cada hora | Cierra las convocatorias de interés vencidas |
| `convocatorias.cerrar_convocatorias_vencidas` | Cada hora | Cierra las convocatorias de solicitud vencidas (RF-043) |
| `prematricula.avisos_y_cierre_prematricula` | Diaria, 7:00 | Aviso de apertura, recordatorios a 5 y 1 días, y paso a *Incompleta* tras el cierre (RF-070) |
| `retencion.aplicar_retencion` | Día 1 de cada mes, 3:00 | Política de retención de datos (RG-028) |

Hay además tareas que se lanzan bajo demanda, al confirmar la transacción:

- correos de las notificaciones;
- correo de activación de cuenta;
- confirmación de la expresión de interés;
- aviso a los interesados al abrir la convocatoria de solicitud.

## Frontend

- **Carpetas:**
  - `components/`: UI reutilizable, layouts, CRUD genérico (`CrudPage`) y
    gráficos SVG propios;
  - `hooks/`: sesión, listados, formularios, polling y archivos privados;
  - `services/`: un cliente por recurso de la API;
  - `pages/`: pantallas públicas, del aspirante y del panel;
  - `utils/`: formato de fechas, archivos y estados.
- **Estilos:** CSS Modules y un único `tokens.css` global. Los colores
  institucionales salen de la identidad visual guardada en la base de datos.
- **Datos que cambian solos:** se consultan cada 60 s con la pestaña visible
  (`usePolling`): campana de notificaciones, estadísticas y dashboards. No se
  usan WebSockets.
