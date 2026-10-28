import { api } from './api'

const datos = (r) => r.data

/** Endpoints públicos de la landing: no requieren sesión. */
export const publico = {
  convocatoriaInteres: () => api.get('/interes/convocatoria/').then((r) => r.data.convocatoria),
  convocatoriaSolicitud: () => api.get('/convocatorias/activa/').then((r) => r.data.convocatoria),
  filtros: () => api.get('/publico/filtros/').then(datos),
  carrera: (id) => api.get(`/carreras/${id}/`).then(datos),
  registrarInteres: (interes) => api.post('/interes/', interes).then(datos),
  /** Oferta de la convocatoria abierta (una tarjeta por carrera y entidad). */
  oferta: { ruta: '/oferta/', listar: (params) => api.get('/oferta/', { params }).then(datos) },
  /** Listado público de otorgados (RF-063): solo verlo, sin descarga. */
  resultados: { ruta: '/publico/resultados/', listar: (params) => api.get('/publico/resultados/', { params }).then(datos) },
  filtrosResultados: () => api.get('/publico/resultados/filtros/').then(datos),
  /** Resultado propio por CI completo (POST: el CI no va en la URL). */
  consultarResultado: (ci) => api.post('/publico/resultados/consulta/', { ci }).then(datos),
  /** Catálogo de carreras, cuando no hay convocatoria abierta. */
  carreras: { ruta: '/carreras/', listar: (params) => api.get('/carreras/', { params }).then(datos) },
}
