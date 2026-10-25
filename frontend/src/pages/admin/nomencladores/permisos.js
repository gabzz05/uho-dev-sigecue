/**
 * Permisos de escritura en la interfaz para los nomencladores.
 * Espeja las reglas de la API: los catálogos globales los modifican solo los
 * roles globales; áreas y departamentos, también los locales en su entidad.
 */
export function permisosNomenclador({ tienePermiso, esGlobal }, { soloGlobales = true } = {}) {
  const puede = (accion) => tienePermiso(`nomencladores.${accion}`) && (esGlobal || !soloGlobales)
  return { crear: puede('crear'), editar: puede('editar'), eliminar: puede('eliminar') }
}
