import { api } from './api'

const BASE = '/admin/otorgamiento/'
const datos = (r) => r.data
const blob = (url, params) => api.get(url, { params, responseType: 'blob' }).then(datos)

/** Otorgamiento de plazas (RF-057 a RF-064, con las decisiones del cliente). */
export const otorgamientos = {
  listar: () => api.get(BASE).then(datos),
  obtener: (id) => api.get(`${BASE}${id}/`).then(datos),
  /** Resumen de elegibilidad antes de generar. */
  previsualizar: (convocatoria) => api.get(`${BASE}previsualizar/`, { params: { convocatoria } }).then(datos),
  generar: (convocatoria) => api.post(BASE, { convocatoria, confirmar: true }).then(datos),
  /** `{ ruta, listar }` para useListado. */
  resultados: (id) => ({ ruta: `${BASE}${id}/resultados/`, listar: (params) => api.get(`${BASE}${id}/resultados/`, { params }).then(datos) }),
  ajustes: (id) => api.get(`${BASE}${id}/ajustes/`).then(datos),
  /** `{ resultado, tipo: 'otorgar'|'quitar', opcion, justificacion }` → `{ ajuste, cambios }`. */
  ajustar: (id, ajuste) => api.post(`${BASE}${id}/ajustar/`, ajuste).then(datos),
  anularAjuste: (id, ajusteId, justificacion) => api.post(`${BASE}${id}/ajustes/${ajusteId}/anular/`, { justificacion }).then(datos),
  aprobar: (id) => api.post(`${BASE}${id}/aprobar/`).then(datos),
  publicar: (id, segundaConvocatoria) => api.post(`${BASE}${id}/publicar/`, { segunda_convocatoria: segundaConvocatoria }).then(datos),
  exportarExcel: (id) => blob(`${BASE}${id}/exportar-excel/`),
  exportarPdf: (id) => blob(`${BASE}${id}/exportar-pdf/`),
}
