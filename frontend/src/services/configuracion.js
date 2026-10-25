import { api } from './api'

const BASE = '/admin/configuracion'
const cuerpo = (r) => r.data

function multipartSiHayArchivo(datos) {
  if (!Object.values(datos).some((v) => v instanceof File)) return datos
  const formulario = new FormData()
  Object.entries(datos).forEach(([clave, valor]) => formulario.append(clave, valor ?? ''))
  return formulario
}

/** Identidad visual pública: la usa toda la app para pintar colores y escudo. */
export const obtenerIdentidad = () => api.get('/identidad/').then(cuerpo)

export const parametros = {
  obtener: () => api.get(`${BASE}/parametros/`).then(cuerpo),
  guardar: (datos) => api.patch(`${BASE}/parametros/`, datos).then(cuerpo),
}

export const smtp = {
  obtener: () => api.get(`${BASE}/smtp/`).then(cuerpo),
  guardar: (datos) => api.patch(`${BASE}/smtp/`, datos).then(cuerpo),
  probar: (destinatario) => api.post(`${BASE}/smtp/probar/`, { destinatario }).then(cuerpo),
}

export const identidad = {
  obtener: () => api.get(`${BASE}/identidad/`).then(cuerpo),
  guardar: (datos) => api.patch(`${BASE}/identidad/`, multipartSiHayArchivo(datos)).then(cuerpo),
}

export const plantillas = {
  listar: () => api.get(`${BASE}/plantillas/`).then(cuerpo),
  guardar: (codigo, datos) => api.patch(`${BASE}/plantillas/${codigo}/`, datos).then(cuerpo),
  restablecer: (codigo) => api.post(`${BASE}/plantillas/${codigo}/restablecer/`).then(cuerpo),
  vistaPrevia: (codigo, datos) => api.post(`${BASE}/plantillas/${codigo}/vista-previa/`, datos).then(cuerpo),
}
