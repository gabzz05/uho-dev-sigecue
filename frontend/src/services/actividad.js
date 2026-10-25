/**
 * Registro de la última interacción del usuario.
 *
 * La sesión solo se renueva si el usuario interactuó en las últimas 8 h
 * (RG-011). Así las peticiones automáticas (p. ej. el polling de
 * notificaciones) no mantienen viva una sesión abandonada.
 */
export const INACTIVIDAD_MAX_MS = 8 * 60 * 60 * 1000

const EVENTOS = ['pointerdown', 'keydown', 'wheel', 'touchstart']

let ultimaActividad = Date.now()

export function registrarActividad() {
  ultimaActividad = Date.now()
}

export function msDesdeUltimaActividad() {
  return Date.now() - ultimaActividad
}

export function hayActividadReciente() {
  return msDesdeUltimaActividad() < INACTIVIDAD_MAX_MS
}

/** Escucha la actividad del usuario. Devuelve la función para dejar de escuchar. */
export function seguirActividad(objetivo = window) {
  EVENTOS.forEach((evento) => objetivo.addEventListener(evento, registrarActividad, { passive: true }))
  return () => EVENTOS.forEach((evento) => objetivo.removeEventListener(evento, registrarActividad))
}
