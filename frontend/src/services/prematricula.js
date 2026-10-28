import { api } from './api'
import { crearRecurso } from './recursos'

const datos = (r) => r.data
const blob = (url, params) => api.get(url, { params, responseType: 'blob' }).then(datos)
const ADMIN = '/admin/prematricula/'

/** Prematrícula del aspirante otorgado (RF-065, RF-067). */
export const miPrematricula = {
  listar: () => api.get('/prematricula/').then(datos),
  obtener: (id) => api.get(`/prematricula/${id}/`).then(datos),
  guardarTexto: (id, elemento, valor) => api.post(`/prematricula/${id}/texto/`, { elemento, valor }).then(datos),
  subirArchivo: (id, elemento, archivo) => {
    const formulario = new FormData()
    formulario.append('elemento', elemento)
    formulario.append('archivo', archivo)
    return api.post(`/prematricula/${id}/archivo/`, formulario).then(datos)
  },
  enviar: (id) => api.post(`/prematricula/${id}/enviar/`).then(datos),
}

/** Panel de prematrícula (RF-068 a RF-072). */
export const prematriculasAdmin = {
  ruta: ADMIN,
  listar: (params) => api.get(ADMIN, { params }).then(datos),
  obtener: (id) => api.get(`${ADMIN}${id}/`).then(datos),
  periodos: () => api.get(`${ADMIN}periodos/`).then(datos),
  opcionesFaltantes: () => api.get(`${ADMIN}faltantes/`).then(datos),
  configurarPeriodo: (periodo) => api.post(`${ADMIN}configurar-periodo/`, periodo).then(datos),
  /** `revision`: 'aprobado' | 'rechazado' (con observación). */
  revisar: (id, elemento, revision, observacion = '') => api.post(`${ADMIN}${id}/revisar/`, { elemento, revision, observacion }).then(datos),
  solicitarCorrecciones: (id) => api.post(`${ADMIN}${id}/solicitar-correcciones/`).then(datos),
  aprobar: (id) => api.post(`${ADMIN}${id}/aprobar/`).then(datos),
  exportarExcel: (params) => blob(`${ADMIN}exportar-excel/`, params),
  exportarPdf: (params) => blob(`${ADMIN}exportar-pdf/`, params),
}

/** Campos del formulario de prematrícula. Los gestiona el Superadmin. */
export const camposPrematricula = crearRecurso('/admin/campos-prematricula/')
