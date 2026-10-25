const SIN_CONEXION = 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.'
const ERROR_GENERICO = 'Ocurrió un error inesperado. Inténtalo más tarde.'

/** Mensaje para el usuario a partir de un error de la API (formato `{error: {mensaje}}`). */
export function mensajeDeError(error) {
  if (!error?.response) return SIN_CONEXION
  return error.response.data?.error?.mensaje ?? ERROR_GENERICO
}

/** Errores por campo de una validación: `{ ci: 'Debe tener 11 dígitos.' }`. */
export function erroresDeCampo(error) {
  const detalles = error?.response?.data?.error?.detalles ?? {}
  return Object.fromEntries(
    Object.entries(detalles).map(([campo, mensajes]) => [campo, Array.isArray(mensajes) ? mensajes.join(' ') : String(mensajes)]),
  )
}
