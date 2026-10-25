import { crearRecurso } from './recursos'

const BASE = '/admin/nomencladores'

export const municipios = crearRecurso(`${BASE}/municipios/`)
export const facultades = crearRecurso(`${BASE}/facultades/`)
export const cumFum = crearRecurso(`${BASE}/cum-fum/`)
export const areas = crearRecurso(`${BASE}/areas/`)
export const departamentos = crearRecurso(`${BASE}/departamentos/`)
export const cargos = crearRecurso(`${BASE}/cargos/`)
export const carreras = crearRecurso(`${BASE}/carreras/`)
