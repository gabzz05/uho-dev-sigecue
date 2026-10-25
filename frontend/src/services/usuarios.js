import { api } from './api'
import { crearRecurso } from './recursos'

const RUTA = '/admin/usuarios/'

export const usuarios = {
  ...crearRecurso(RUTA),
  /** Roles que el usuario actual puede asignar (no exige `roles.ver`). */
  rolesAsignables: () => api.get(`${RUTA}roles-asignables/`).then((r) => r.data),
  bloquear: (id) => api.post(`${RUTA}${id}/bloquear/`).then((r) => r.data),
  desbloquear: (id) => api.post(`${RUTA}${id}/desbloquear/`).then((r) => r.data),
}

export const roles = {
  ...crearRecurso('/admin/roles/'),
  /** Permisos disponibles agrupados por módulo. */
  catalogo: () => api.get('/admin/roles/catalogo/').then((r) => r.data),
}
