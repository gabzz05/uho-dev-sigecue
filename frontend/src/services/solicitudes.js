import { api } from './api'

const BASE = '/admin/solicitudes/'
const datos = (r) => r.data
const blob = (url, params) => api.get(url, { params, responseType: 'blob' }).then(datos)

/** Gestión de solicitudes por las entidades (RF-052 a RF-056). */
export const solicitudesAdmin = {
  ruta: BASE,
  listar: (params) => api.get(BASE, { params }).then(datos),
  obtener: (id) => api.get(`${BASE}${id}/`).then(datos),
  validarIndice: (id, indice) => api.post(`${BASE}${id}/validar-indice/`, { indice }).then(datos),
  /** `{ objetivo, tipo_documento?, texto, afecta_elegibilidad? }`. Devuelve el detalle actualizado. */
  observar: (id, observacion) => api.post(`${BASE}${id}/observar/`, observacion).then(datos),
  estadisticas: (params) => api.get(`${BASE}estadisticas/`, { params }).then(datos),
  exportarExcel: (params) => blob(`${BASE}exportar-excel/`, params),
  exportarPdf: (params) => blob(`${BASE}exportar-pdf/`, params),
}

/** Observaciones: cada entidad gestiona las suyas; los roles globales, cualquiera (RF-055). */
export const observaciones = {
  editar: (id, cambios) => api.patch(`/admin/observaciones/${id}/`, cambios).then(datos),
  resolver: (id) => api.post(`/admin/observaciones/${id}/resolver/`).then(datos),
  reabrir: (id, motivo) => api.post(`/admin/observaciones/${id}/reabrir/`, { motivo }).then(datos),
}
