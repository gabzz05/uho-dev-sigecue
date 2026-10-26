import { api } from './api'
import { crearRecurso } from './recursos'

const BASE = '/admin/plan-plazas/'
const datos = (r) => r.data
const blob = (url) => api.get(url, { responseType: 'blob' }).then(datos)
const accion = (id, nombre, cuerpo) => api.post(`${BASE}${id}/${nombre}/`, cuerpo).then(datos)

/** Planes de plazas y sus transiciones (RF-032 a RF-039). Cada acción devuelve el plan actualizado. */
export const planes = {
  ...crearRecurso(BASE),
  enviar: (id) => accion(id, 'enviar'),
  cargarOferta: (id) => accion(id, 'cargar-oferta'),
  cerrarRevision: (id, forzar = false) => accion(id, 'cerrar-revision', { forzar }),
  generarVersionFinal: (id) => accion(id, 'generar-version-final'),
  enviarPropuesta: (id, texto) => accion(id, 'enviar-propuesta', { texto }),
  aprobar: (id) => accion(id, 'aprobar'),
  devolver: (id, texto) => accion(id, 'devolver', { texto }),
  complementaria: (id, texto) => accion(id, 'complementaria', { texto }),
  historial: (id) => api.get(`${BASE}${id}/historial/`).then(datos),
  comentarios: (id) => api.get(`${BASE}${id}/comentarios/`).then(datos),
  comentar: (id, texto, linea) => api.post(`${BASE}${id}/comentarios/`, { texto, linea }).then(datos),
  exportarPdf: (id) => blob(`${BASE}${id}/exportar-pdf/`),
  exportarExcel: (id) => blob(`${BASE}${id}/exportar-excel/`),
}

const LINEAS = `${BASE}lineas/`

export const lineasPlan = {
  listar: (plan) => api.get(LINEAS, { params: { plan } }).then(datos),
  crear: (linea) => api.post(LINEAS, linea).then(datos),
  actualizar: (id, plazas) => api.patch(`${LINEAS}${id}/`, { plazas_propuestas: plazas }).then(datos),
  eliminar: (id) => api.delete(`${LINEAS}${id}/`),
  responder: (id, respuesta) => api.post(`${LINEAS}${id}/responder/`, respuesta).then(datos),
  decidir: (id, decision) => api.post(`${LINEAS}${id}/decidir/`, decision).then(datos),
}
