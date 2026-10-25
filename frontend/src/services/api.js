import axios from 'axios'
import { hayActividadReciente } from './actividad'
import { tokenStore } from './tokenStore'

export const API_BASE = '/api/v1'

/** Cliente HTTP de la aplicación: añade el access token y renueva la sesión ante un 401. */
export const api = axios.create({ baseURL: API_BASE, withCredentials: true })

// Cliente sin interceptores para el refresh, así un 401 del refresh no entra en bucle.
const apiSinInterceptores = axios.create({ baseURL: API_BASE, withCredentials: true })

let renovacionEnCurso = null
let alExpirarSesion = () => {}

/** Registra qué hacer cuando la sesión no se puede renovar (lo usa AuthProvider). */
export function onSesionExpirada(manejador) {
  alExpirarSesion = manejador
}

/**
 * Pide un access token nuevo con la cookie de refresh.
 * Las llamadas simultáneas comparten la misma petición: el refresh rota en
 * cada uso, y dos peticiones en paralelo invalidarían la sesión.
 */
export function renovarSesion() {
  if (!hayActividadReciente()) {
    return Promise.reject(new Error('Sesión inactiva'))
  }
  renovacionEnCurso ??= apiSinInterceptores
    .post('/auth/refresh/')
    .then(({ data }) => {
      tokenStore.set(data.access)
      return data.access
    })
    .finally(() => {
      renovacionEnCurso = null
    })
  return renovacionEnCurso
}

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const esRutaDeSesion = config?.url?.startsWith('/auth/')
    if (response?.status !== 401 || !config || config._reintentado || esRutaDeSesion) {
      throw error
    }
    try {
      await renovarSesion()
    } catch {
      tokenStore.clear()
      alExpirarSesion()
      throw error
    }
    config._reintentado = true
    return api(config)
  },
)
