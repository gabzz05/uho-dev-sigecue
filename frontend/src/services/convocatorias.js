import { api } from './api'
import { crearRecurso } from './recursos'

const BASE = '/admin/convocatorias/'

/** Convocatorias de solicitud de matrícula (RF-040 a RF-043). */
export const convocatoriasSolicitud = {
  ...crearRecurso(BASE),
  abrir: (id) => api.post(`${BASE}${id}/abrir/`).then((r) => r.data),
  cerrar: (id) => api.post(`${BASE}${id}/cerrar/`).then((r) => r.data),
}
