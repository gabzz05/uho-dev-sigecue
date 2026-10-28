# Manual de uso por rol

Qué hace cada rol en cada etapa del proceso de ingreso. Al entrar al panel, el
**Dashboard** muestra a cada uno sus pendientes en "Requiere atención".

## El proceso, de principio a fin

| # | Etapa | Quién la lleva | Dónde |
|---|---|---|---|
| 1 | Convocatoria de interés y oferta | Comisión de Ingreso (CI) y entidades | Interés de la población |
| 2 | Expresión de interés de la población | Ciudadanos (sin registro) | Landing |
| 3 | Plan de plazas | CI → entidades → CI → Vicerrector | Plan de Plazas |
| 4 | Convocatoria de solicitud | CI / Secretaría General | Convocatorias |
| 5 | Registro, perfil y solicitud | Aspirantes | Portal del aspirante |
| 6 | Revisión de solicitudes | Secretarías y Admins de las entidades | Solicitudes |
| 7 | Otorgamiento | Secretaría General → Jefe CI → Vicerrector | Otorgamiento |
| 8 | Resultados públicos | Todos | Landing → Resultados |
| 9 | Prematrícula | Secretaría General, aspirantes otorgados y entidades | Prematrícula |

## Aspirante

1. **Registrarse** (desde "Solicitar matrícula" en la landing): nombre,
   apellidos, CI, correo, celular y contraseña, aceptando la política de
   privacidad. Llega un correo de activación, que vale 48 horas.
2. **Completar el perfil** (Mi perfil de aspirante):
   - foto;
   - centro de trabajo;
   - índice académico;
   - CI por ambas caras y certificación de estudios (PDF, JPG o PNG, de 5 MB
     como máximo).
3. **Mi solicitud:**
   - "Nueva solicitud";
   - agregar carreras del catálogo y ordenarlas por prioridad, arrastrando o
     con los botones subir y bajar;
   - "Guardar cambios" y "Confirmar solicitud". Llega un resumen por correo.

   Se puede cambiar mientras la convocatoria esté abierta.
4. **Si hay observaciones:** se avisa por correo. Hay que corregir lo
   observado en el perfil y pulsar **Enviar corrección** en Mi solicitud. Se
   puede corregir aunque la convocatoria haya cerrado, pero solo lo observado.
5. **Resultado:** llega un aviso al publicarse. También se consulta en la
   landing → Resultados, con el CI completo.
6. **Prematrícula** (solo los otorgados): subir la foto tipo carné, la carta
   del centro de trabajo y la solicitud firmada. El CI y la certificación se
   toman del perfil. Se puede guardar por partes y después se pulsa **Enviar**.
   Si hay correcciones, hay que corregir lo rechazado y reenviar. No se pierde
   la plaza.

## Secretario(a) y Admin de Facultad o CUM/FUM

**Interés.** En la pestaña Oferta se agregan las carreras de la entidad. Las
asignadas por la CI no se pueden quitar. La pestaña Dashboard muestra el
interés recibido en la entidad.

**Plan de plazas** (Admin, Vicedecano o Director). Se revisa la propuesta de la
entidad y, en cada carrera, se puede aceptar, ajustar la cantidad, pedir
quitarla o agregar otra, siempre con justificación. Después se envía la
propuesta.

**Solicitudes.** Se ven solo las opciones de la entidad. Dentro de cada
solicitud:
- **Validar índice:** se escribe el valor que figura en la certificación. Solo
  una entidad lo valida.
- **Nueva observación:** sobre un documento, el índice, el centro de trabajo o
  la foto. Si "afecta la elegibilidad", anula el índice validado.
- Cuando el aspirante corrige, la observación se **resuelve** o se **reabre**,
  explicando el motivo.

Una solicitud con observaciones sin resolver no entra en el otorgamiento.

**Prematrícula.** En cada expediente, cada documento se aprueba o se rechaza
(rechazar exige una observación). Después se pulsa **Solicitar correcciones**
o **Aprobar prematrícula**. El filtro "Le falta…" sirve para el seguimiento.

**Documentos.** Abrirlos exige el permiso de descarga, que por defecto tienen
los secretarios y el Director(a) de CUM/FUM. Cada apertura queda registrada.

## Jefe(a) de la Comisión de Ingreso

- **Interés:**
  - crear y abrir la convocatoria de interés del año;
  - asignar carreras a las entidades.
- **Plan de plazas:**
  - crear el plan y enviarlo a las entidades;
  - fijar el valor final de cada línea;
  - generar la versión final para el Vicerrector.
- **Convocatorias:**
  - crearlas y abrirlas; exigen el plan publicado;
  - la primera convocatoria avisa a los interesados.
- **Solicitudes:** ve todas, puede revisar y cambiar un índice ya validado.
- **Otorgamiento** (etapa "Revisión del Jefe CI"):
  - revisar el reparto;
  - **Ajustar** a un aspirante: otorgar otra de sus carreras o quitarle una,
    siempre con justificación. El sistema recalcula en cascada y muestra qué
    cambió;
  - **Aprobar**.

## Secretaría General

- **Convocatorias:** crear y gestionar las convocatorias de solicitud.
- **Otorgamiento:** con la convocatoria cerrada, **Generar otorgamiento**. Se
  revisa el resumen de elegibles y no elegibles y se confirma. Se ejecuta una
  sola vez.
- **Prematrícula:** fijar el período (inicio y cierre). Con eso se crean los
  expedientes, se avisa a los otorgados y queda fijada la vigencia del listado
  público.

## Vicerrector(a) de Formación

- **Plan de plazas:** revisar y aprobar. La aprobación publica el plan.
- **Otorgamiento** (etapa "Aprobación del Vicerrector"):
  - revisar y ajustar si hace falta;
  - **Aprobar y publicar**, indicando si habrá segunda convocatoria;
  - el resultado queda congelado y se avisa a todos los aspirantes.

## Superadmin

- **Configuración:**
  - parámetros: máximo de carreras, intentos de acceso y plazos de retención;
  - correo SMTP, con envío de prueba;
  - plantillas de correo;
  - identidad visual: nombre, colores y escudo;
  - documentos del aspirante;
  - campos de prematrícula;
  - **retención de datos**: vista previa y ejecución adelantada.
- **Usuarios y roles:** alta de usuarios internos y asignación de entidad y
  rol. Los usuarios no se borran: se desactivan. La matriz de permisos se
  edita por rol.
- **Logs de auditoría:** consulta de toda la actividad.
- **Nomencladores:** Facultades, CUM/FUM, carreras, áreas, departamentos,
  cargos y municipios.

## Jefe(a) de Área, Vicedecano(a) y Director(a) de CUM/FUM

Consultan los módulos de su entidad (interés, plan, solicitudes, otorgamiento
publicado y prematrícula) y los dashboards. Además:
- el Jefe de Área comenta en el plan de plazas;
- el Vicedecano y el Director responden la propuesta del plan;
- el Director de CUM/FUM puede abrir los documentos de los aspirantes de su
  CUM, pero no revisa solicitudes ni prematrículas.
