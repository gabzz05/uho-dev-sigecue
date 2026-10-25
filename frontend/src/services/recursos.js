import { api } from './api'

/** Convierte a multipart si hay archivos. Una cadena vacía en un campo de archivo lo borra. */
function cuerpo(datos) {
  const conArchivo = Object.values(datos).some((v) => v instanceof File)
  if (!conArchivo) return datos
  const formulario = new FormData()
  Object.entries(datos).forEach(([clave, valor]) => {
    if (valor === undefined) return
    formulario.append(clave, valor === null ? '' : valor)
  })
  return formulario
}

/**
 * Un campo de archivo que sigue siendo la URL ya guardada no se reenvía.
 * `File` = archivo nuevo; '' = quitarlo.
 */
export function omitirArchivoSinCambios(datos, campo = 'imagen') {
  const valor = datos[campo]
  if (typeof valor !== 'string' || valor === '') return datos
  const { [campo]: _omitido, ...resto } = datos // eslint-disable-line no-unused-vars
  return resto
}

/**
 * Cliente CRUD de un recurso REST de la API (`/admin/nomencladores/carreras/`...).
 * `listar` devuelve la respuesta paginada `{count, next, previous, results}`.
 */
export function crearRecurso(ruta) {
  return {
    ruta,
    listar: (params) => api.get(ruta, { params }).then((r) => r.data),
    crear: (datos) => api.post(ruta, cuerpo(datos)).then((r) => r.data),
    actualizar: (id, datos) => api.patch(`${ruta}${id}/`, cuerpo(datos)).then((r) => r.data),
    eliminar: (id) => api.delete(`${ruta}${id}/`),
  }
}
