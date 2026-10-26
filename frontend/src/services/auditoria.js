import { api } from './api'

const RUTA = '/admin/logs/'

/** Logs de auditoría (RG-010). Solo lectura. */
export const logs = {
  ruta: RUTA,
  listar: (params) => api.get(RUTA, { params }).then((r) => r.data),
  modulos: () => api.get(`${RUTA}modulos/`).then((r) => r.data.modulos),
}
