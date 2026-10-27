import { api } from './api'
import { crearRecurso } from './recursos'

/** Perfil del aspirante autenticado (RF-046). La foto se cambia con `actualizarPerfil` (services/perfil). */
export const perfilAspirante = {
  obtener: () => api.get('/aspirante/perfil/').then((r) => r.data),
  actualizar: (datos) => api.patch('/aspirante/perfil/', datos).then((r) => r.data),
  /** Sube o sustituye el documento de un tipo. Devuelve el perfil actualizado. */
  subirDocumento: (tipo, archivo) => {
    const datos = new FormData()
    datos.append('tipo', tipo)
    datos.append('archivo', archivo)
    return api.post('/aspirante/documentos/', datos).then((r) => r.data)
  },
}

/** Solicitudes de carrera del aspirante (RF-047 a RF-051). */
export const solicitudes = {
  listar: () => api.get('/solicitudes/').then((r) => r.data),
  /** Crea el borrador en la convocatoria abierta (o devuelve el existente). */
  crear: () => api.post('/solicitudes/').then((r) => r.data),
  guardarCarreras: (id, ofertas) => api.put(`/solicitudes/${id}/carreras/`, { ofertas }).then((r) => r.data),
  confirmar: (id) => api.post(`/solicitudes/${id}/confirmar/`).then((r) => r.data),
  /** Da por corregido lo observado; vale también con la convocatoria cerrada. */
  enviarCorreccion: (id) => api.post(`/solicitudes/${id}/enviar-correccion/`).then((r) => r.data),
  ofertas: () => api.get('/solicitudes/ofertas/').then((r) => r.data),
}

/** Archivo privado (foto, documentos) pedido con el token. `ruta` es relativa a la API. */
export function obtenerArchivo(ruta) {
  return api.get(ruta, { responseType: 'blob' }).then((r) => r.data)
}

/** Catálogo de documentos que se piden al aspirante. Lo gestiona el Superadmin. */
export const tiposDocumento = crearRecurso('/admin/tipos-documento/')
