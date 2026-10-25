import { api, renovarSesion } from './api'
import { tokenStore } from './tokenStore'

export async function iniciarSesion(identificador, password) {
  const { data } = await api.post('/auth/login/', { identificador, password })
  tokenStore.set(data.access)
  return data.usuario
}

export async function cerrarSesion() {
  try {
    await api.post('/auth/logout/')
  } finally {
    tokenStore.clear()
  }
}

export async function obtenerPerfil() {
  const { data } = await api.get('/auth/me/')
  return data
}

/** Al cargar la app: si la cookie de refresh sigue vigente, recupera la sesión. */
export async function restaurarSesion() {
  try {
    await renovarSesion()
  } catch {
    return null
  }
  return obtenerPerfil()
}

export async function registrarAspirante(datos) {
  const { data } = await api.post('/auth/registro/', datos)
  return data.mensaje
}

export async function activarCuenta(token) {
  const { data } = await api.post('/auth/activar/', { token })
  return data.mensaje
}
