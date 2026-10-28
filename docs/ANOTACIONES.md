# Anotaciones

Elementos que hoy están resueltos de forma provisional porque falta material
externo, y qué hacer cuando ese material llegue.

## Pendientes que debe aportar la UHO

| # | Qué | Para qué | Dónde se integra |
|---|---|---|---|
| 1 | GeoJSON (o SVG) de los 14 municipios | Mapa real del dashboard de interés (RF-029) | Componente con la misma interfaz que `MapaMunicipios` (§1) |
| 2 | Escudo y Manual de Identidad Visual | Interfaz y membrete de los PDF (RE-001, RE-009) | Configuración → Identidad visual (§2, §6) |
| 3 | Texto oficial de la política de privacidad | Consentimiento del registro (RG-024, RG-026) | `pages/public/Privacidad.jsx` (§3) |
| 4 | Misión, visión y datos de contacto | Sección institucional de la landing (RF-025) | `SeccionInstitucional.jsx` (§4) |
| 5 | Datos de conexión al SGU (auth.uho.edu.cu) | Acceso de los roles internos (RF-012, RE-002) | [SGU.md](SGU.md) (§7) |
| 6 | Acceso a SIGENU y ASSET | Validar el índice y el centro de trabajo (RG-014, RG-015) | §8 |
| 7 | Infraestructura para pruebas de carga | Comprobar tiempos y concurrencia (RG-023, RNF-001 a RNF-003) | §9 |

## 1. Mapa de interés por municipio (RF-029)

**Qué es:** el dashboard de la convocatoria de interés debe mostrar cuánto
interés hay en cada municipio, sobre un mapa de la provincia de Holguín.
Cada municipio se colorea más intenso cuanto más expresiones de interés
recibieron las carreras que se ofertan allí.

**Estado actual: provisional.** `frontend/src/components/graficos/MapaMunicipios.jsx`
dibuja una casilla por municipio en su posición aproximada (tabla `POSICIONES`,
columna y fila). El color es una escala secuencial de un solo tono, cada
casilla lleva el número escrito y debajo hay una tabla con los mismos datos.
El interés se cuenta por el **municipio de la entidad que oferta la carrera**.

**Qué hace falta:** un archivo con los contornos de los 14 municipios de
Holguín, preferiblemente **GeoJSON** (o un SVG con un `<path>` por municipio).
Cada contorno debe poder relacionarse con un municipio del nomenclador, por
nombre o por código.

**Cómo integrarlo cuando llegue:**

1. Guardar el GeoJSON en `frontend/src/assets/` (o el SVG con un `<path>` por
   municipio).
2. Crear un componente con la **misma interfaz** que `MapaMunicipios`:
   `filas = [{ municipio, nombre, total }]`. La API ya devuelve los 14
   municipios en `/admin/interes/expresiones/estadisticas/` (`por_municipio`).
3. Relacionar cada contorno con el municipio por nombre, o por un código si se
   añade al nomenclador.
4. Reutilizar la misma escala de color (`n0` a `n5`), el número en el tooltip
   y la tabla complementaria, y sustituir el componente en
   `pages/admin/interes/DashboardInteres.jsx`.

## 2. Escudo de la UHO (RE-001, RE-009)

**Estado actual:** no se tiene el archivo. La interfaz muestra un distintivo
"UHO" en su lugar.

**Cómo integrarlo:** subirlo desde Configuración → Identidad visual. La interfaz
y el membrete de los PDF (`core/pdf.py`) lo usan en cuanto se guarda.

**Qué hace falta:** el escudo en SVG (preferido) o PNG de alta resolución, y el
Manual de Identidad Visual si existe.

## 3. Texto de la Política de Privacidad (RG-026)

**Estado actual:** la página `/privacidad` existe y el registro enlaza a ella,
pero muestra un aviso de "texto pendiente".

**Qué hace falta:** el texto oficial de la política de privacidad de la UHO
(Decreto-Ley 370/2019, RG-024).

**Cómo integrarlo:** sustituir el contenido de
`frontend/src/pages/public/Privacidad.jsx`.

## 4. Sección institucional de la landing (RF-025)

**Estado actual:** misión, visión, dirección, teléfono y correo son textos
provisionales (teléfono y correo dicen "Pendiente").

**Qué hace falta:** los textos oficiales de la UHO.

**Cómo integrarlo:** editar la constante `TEXTOS` en
`frontend/src/components/landing/SeccionInstitucional/SeccionInstitucional.jsx`.
Si más adelante se quiere editarlos desde el panel, se pueden guardar en la
configuración del sistema como la identidad visual.

## 5. Fotos de perfil (archivos privados)

**Resuelto** (feature `portal-aspirante`). La foto y los documentos se guardan
en el almacenamiento privado (`MEDIA_ROOT`), que no se publica. La API los sirve
con control de acceso:

- `/auth/me/foto/`: la foto propia;
- `/documentos/{id}/archivo/`: un documento;
- `/admin/aspirantes/{id}/foto/`: la foto de un aspirante, para el personal.

El frontend los pide con el token y los muestra como `blob:`
(`useArchivoPrivado`), porque un `<img>` no puede enviar la cabecera
`Authorization`. El visor inline de RF-054 usará los mismos endpoints.

## 6. Identidad visual

**Estado actual:** se usa la paleta del mockup como valor inicial. El Superadmin
la cambia en Configuración → Identidad visual y el frontend la aplica al
cargar. `frontend/src/styles/tokens.css` contiene los valores por defecto, que
se usan si la API no responde.

## 7. Autenticación con el SGU (RF-012, RE-002)

**Estado actual:** los roles internos entran con usuario y contraseña locales.
El adaptador (`backend/apps/users/sgu.py`) está preparado y desactivado
(`SGU_PROVEEDOR` vacío).

**Qué hace falta:** el protocolo (LDAP u OAuth 2.0 / OpenID Connect), la URL,
las credenciales de la aplicación y el atributo que identifica al usuario.

**Cómo integrarlo:** seguir [SGU.md](SGU.md).

## 8. SIGENU y ASSET (RG-014, RG-015)

**Estado actual:** no hay integración.

- El índice académico lo declara el aspirante y lo **valida a mano** una
  entidad contra la certificación (`indice_validado`). Solo el índice validado
  cuenta para el ranking.
- El centro de trabajo es **texto libre**.

**Qué hace falta:** acceso a las API (o vistas de base de datos) de SIGENU y
ASSET, con su documentación.

**Cómo integrarlo:**

- **SIGENU:** un adaptador como el del SGU, que consulte el índice por CI y lo
  proponga al validar (`solicitudes/revision.py`, `validar_indice`), sin
  quitar la validación de la entidad.
- **ASSET:** se consulta al guardar el perfil, solo como referencia del centro
  de trabajo (`aspirantes/services.py`, `actualizar_datos`).

## 9. Rendimiento y disponibilidad (RG-023, RNF-001 a RNF-003)

**Estado actual:** no medido. El sistema pagina las listas, carga las
relaciones de cada consulta en bloque (`select_related` / `prefetch_related`),
comprime las respuestas con gzip y difiere la carga de las imágenes de la
landing. Los servicios se reinician solos (systemd).

**Qué hace falta:** un entorno equivalente al de producción para una prueba de
carga (100 y 500 usuarios concurrentes), con la herramienta que elija la
Dirección de Informatización.
