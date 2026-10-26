import { api } from './api'

const MIAS = '/notificaciones/'
const ENVIOS = '/admin/notificaciones/envios/'
const datos = (r) => r.data

/** Notificaciones del usuario autenticado. */
export const notificaciones = {
  ruta: MIAS,
  noLeidas: () => api.get(`${MIAS}no-leidas/`).then((r) => r.data.no_leidas),
  listar: (params) => api.get(MIAS, { params }).then(datos),
  leer: (id) => api.post(`${MIAS}${id}/leer/`).then(datos),
  leerTodas: () => api.post(`${MIAS}leer-todas/`).then(datos),
  eliminar: (id) => api.delete(`${MIAS}${id}/`),
}

/** Envíos masivos (RF-076). */
export const envios = {
  ruta: ENVIOS,
  listar: (params) => api.get(ENVIOS, { params }).then(datos),
  crear: (envio) => api.post(ENVIOS, envio).then(datos),
  contar: (grupo) => api.post(`${ENVIOS}contar/`, grupo).then(datos),
}
