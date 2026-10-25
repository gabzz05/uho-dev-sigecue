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

**Estado actual:** no se tiene el archivo. La interfaz y los PDF reservan su
espacio.

**Qué hace falta:** el escudo en SVG (preferido) o PNG de alta resolución, y el
Manual de Identidad Visual si existe.

## 3. Texto de la Política de Privacidad (RG-026)

**Estado actual:** la página `/privacidad` existe y el registro enlaza a ella,
pero muestra un aviso de "texto pendiente".

**Qué hace falta:** el texto oficial de la política de privacidad de la UHO
(Decreto-Ley 370/2019, RG-024).

**Cómo integrarlo:** sustituir el contenido de
`frontend/src/pages/public/Privacidad.jsx`.

## 4. Identidad visual

**Estado actual:** se usa la paleta del mockup. Los colores se guardan en base
de datos (los define el Superadmin) y el frontend los aplica al cargar.
`frontend/src/styles/tokens.css` contiene los valores por defecto.
