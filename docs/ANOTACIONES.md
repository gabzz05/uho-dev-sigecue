# Anotaciones

Elementos que hoy están resueltos de forma provisional porque falta material
externo, y qué hacer cuando ese material llegue.

## 1. Mapa de interés por municipio (RF-029)

**Qué es:** el dashboard de la convocatoria de interés debe mostrar cuánto
interés hay en cada municipio, sobre un mapa de la provincia de Holguín.
Cada municipio se colorea más intenso cuanto más expresiones de interés
recibieron las carreras que se ofertan allí.

**Estado actual:** pendiente de la geometría real de los municipios.
La solución provisional se describirá aquí cuando se implemente el dashboard
(feature `convocatoria-interes`).

**Qué hace falta:** un archivo con los contornos de los 14 municipios de
Holguín, preferiblemente **GeoJSON** (o un SVG con un `<path>` por municipio).
Cada contorno debe poder relacionarse con un municipio del nomenclador, por
nombre o por código.

**Cómo integrarlo cuando llegue:** se completará con los pasos concretos
cuando exista el componente del mapa.

## 2. Escudo de la UHO (RE-001, RE-009)

**Estado actual:** no se tiene el archivo. La interfaz muestra un distintivo
"UHO" en su lugar.

**Cómo integrarlo:** subirlo desde Configuración → Identidad visual. La interfaz
lo usa en cuanto se guarda; los PDF lo tomarán de ahí (feature de exportaciones).

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

**Estado actual:** la foto de perfil se guarda en el almacenamiento privado
(`MEDIA_ROOT`), que no se publica. Su URL todavía no se puede abrir, así que el
avatar muestra las iniciales.

**Pendiente** (feature `portal-aspirante`): un endpoint de descarga con control
de permisos para los archivos privados. Servirá para la foto, el CI y la
certificación del aspirante, y para el visor de documentos de RF-054. El
frontend los pedirá con el token y los mostrará como `blob:`, porque un
`<img>` no puede enviar la cabecera `Authorization`.

## 6. Identidad visual

**Estado actual:** se usa la paleta del mockup como valor inicial. El Superadmin
la cambia en Configuración → Identidad visual y el frontend la aplica al
cargar. `frontend/src/styles/tokens.css` contiene los valores por defecto, que
se usan si la API no responde.
