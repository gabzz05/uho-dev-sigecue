import axios from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Las instancias de axios copian `axios.defaults.adapter` al crearse, así que
 * se fija un adaptador falso y se importa el módulo de cero en cada prueba.
 */
function respuesta(config, status, data = {}) {
  const res = { data, status, statusText: '', headers: {}, config }
  if (status >= 400) {
    const error = new axios.AxiosError('error', String(status), config, null, res)
    return Promise.reject(error)
  }
  return Promise.resolve(res)
}

let rutas
let llamadas
const adaptadorOriginal = axios.defaults.adapter

async function cargar() {
  vi.resetModules()
  const api = await import('./api')
  const { tokenStore } = await import('./tokenStore')
  const actividad = await import('./actividad')
  return { ...api, tokenStore, actividad }
}

beforeEach(() => {
  llamadas = []
  rutas = {}
  axios.defaults.adapter = (config) => {
    llamadas.push({ url: config.url, auth: config.headers.Authorization })
    const manejador = rutas[config.url]
    return manejador ? manejador(config) : respuesta(config, 404)
  }
})

afterEach(() => {
  axios.defaults.adapter = adaptadorOriginal
  vi.useRealTimers()
})

describe('cliente api', () => {
  it('añade el access token a las peticiones', async () => {
    const { api, tokenStore } = await cargar()
    tokenStore.set('abc')
    rutas['/carreras/'] = (c) => respuesta(c, 200, [])

    await api.get('/carreras/')

    expect(llamadas[0].auth).toBe('Bearer abc')
  })

  it('ante un 401 renueva la sesión y reintenta con el token nuevo', async () => {
    const { api, tokenStore } = await cargar()
    tokenStore.set('viejo')
    rutas['/auth/refresh/'] = (c) => respuesta(c, 200, { access: 'nuevo' })
    rutas['/privado/'] = (c) => respuesta(c, c.headers.Authorization === 'Bearer nuevo' ? 200 : 401, { ok: true })

    const { data } = await api.get('/privado/')

    expect(data).toEqual({ ok: true })
    expect(tokenStore.get()).toBe('nuevo')
  })

  it('peticiones simultáneas comparten una sola renovación', async () => {
    const { api } = await cargar()
    rutas['/auth/refresh/'] = (c) => respuesta(c, 200, { access: 'nuevo' })
    rutas['/a/'] = (c) => respuesta(c, c.headers.Authorization ? 200 : 401)
    rutas['/b/'] = (c) => respuesta(c, c.headers.Authorization ? 200 : 401)

    await Promise.all([api.get('/a/'), api.get('/b/')])

    expect(llamadas.filter((l) => l.url === '/auth/refresh/')).toHaveLength(1)
  })

  it('si no se puede renovar, avisa de la sesión expirada y limpia el token', async () => {
    const { api, tokenStore, onSesionExpirada } = await cargar()
    const expirada = vi.fn()
    onSesionExpirada(expirada)
    tokenStore.set('viejo')
    rutas['/auth/refresh/'] = (c) => respuesta(c, 401)
    rutas['/privado/'] = (c) => respuesta(c, 401)

    await expect(api.get('/privado/')).rejects.toBeDefined()

    expect(expirada).toHaveBeenCalled()
    expect(tokenStore.get()).toBeNull()
  })

  it('sin actividad del usuario en 8 h no renueva la sesión', async () => {
    vi.useFakeTimers()
    const { api, onSesionExpirada, actividad } = await cargar()
    const expirada = vi.fn()
    onSesionExpirada(expirada)
    rutas['/auth/refresh/'] = (c) => respuesta(c, 200, { access: 'nuevo' })
    rutas['/notificaciones/'] = (c) => respuesta(c, 401)

    vi.advanceTimersByTime(actividad.INACTIVIDAD_MAX_MS + 1)
    await expect(api.get('/notificaciones/')).rejects.toBeDefined()

    expect(llamadas.some((l) => l.url === '/auth/refresh/')).toBe(false)
    expect(expirada).toHaveBeenCalled()
  })

  it('la actividad del usuario vuelve a permitir la renovación', async () => {
    vi.useFakeTimers()
    const { renovarSesion, actividad } = await cargar()
    rutas['/auth/refresh/'] = (c) => respuesta(c, 200, { access: 'nuevo' })

    vi.advanceTimersByTime(actividad.INACTIVIDAD_MAX_MS + 1)
    const limpiar = actividad.seguirActividad()
    window.dispatchEvent(new Event('keydown'))
    limpiar()

    await expect(renovarSesion()).resolves.toBe('nuevo')
  })

  it('un 401 en rutas de sesión no intenta renovar', async () => {
    const { api } = await cargar()
    rutas['/auth/login/'] = (c) => respuesta(c, 401)

    await expect(api.post('/auth/login/')).rejects.toBeDefined()

    expect(llamadas.map((l) => l.url)).toEqual(['/auth/login/'])
  })
})

describe('errores', () => {
  it('extrae el mensaje y los errores por campo del formato de la API', async () => {
    const { mensajeDeError, erroresDeCampo } = await import('./errores')
    const error = {
      response: { data: { error: { mensaje: 'Revisa los datos', detalles: { ci: ['Debe tener 11 dígitos.'] } } } },
    }

    expect(mensajeDeError(error)).toBe('Revisa los datos')
    expect(erroresDeCampo(error)).toEqual({ ci: 'Debe tener 11 dígitos.' })
  })

  it('sin respuesta del servidor indica problema de conexión', async () => {
    const { mensajeDeError } = await import('./errores')
    expect(mensajeDeError(new Error('Network Error'))).toMatch(/conectar/)
  })
})
