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

## 3. Identidad visual

**Estado actual:** se usa la paleta del mockup. Los colores se guardan en base
de datos (los define el Superadmin) y el frontend los aplica al cargar.
`frontend/src/styles/tokens.css` contiene los valores por defecto.
