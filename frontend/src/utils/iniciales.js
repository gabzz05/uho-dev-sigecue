/** Iniciales de un nombre: "María González Pérez" → "MG". */
export function iniciales(nombre = '') {
  return nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')
}
