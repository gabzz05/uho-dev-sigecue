import { api } from './api'
import { crearRecurso } from './recursos'

const BASE = '/admin/interes'

export const convocatoriasInteres = {
  ...crearRecurso(`${BASE}/convocatorias/`),
  abrir: (id) => api.post(`${BASE}/convocatorias/${id}/abrir/`).then((r) => r.data),
  cerrar: (id) => api.post(`${BASE}/convocatorias/${id}/cerrar/`).then((r) => r.data),
}

export const ofertas = crearRecurso(`${BASE}/ofertas/`)

export const expresiones = {
  ...crearRecurso(`${BASE}/expresiones/`),
  /** Excel de interesados con los mismos filtros del listado (RF-031). */
  /** Dashboard de interés (RF-029) con los mismos filtros y ámbito que el listado. */
  estadisticas: (params) => api.get(`${BASE}/expresiones/estadisticas/`, { params }).then((r) => r.data),
  exportar: (params) => api.get(`${BASE}/expresiones/exportar/`, { params, responseType: 'blob' }).then((r) => r.data),
}
