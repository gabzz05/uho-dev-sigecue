import { useEffect } from 'react'

export const INTERVALO_POLLING_MS = 60_000

/**
 * Ejecuta `actualizar` al montar y cada 60 s, solo con la pestaña visible;
 * al volver a la pestaña lo ejecuta enseguida. `actualizar` debe ser estable.
 * El polling no renueva la sesión por sí solo (ver services/actividad.js).
 */
export function usePolling(actualizar, intervalo = INTERVALO_POLLING_MS) {
  useEffect(() => {
    let temporizador = null
    function iniciar() {
      clearInterval(temporizador)
      temporizador = setInterval(actualizar, intervalo)
    }
    function alCambiarVisibilidad() {
      if (document.visibilityState === 'visible') {
        actualizar()
        iniciar()
      } else {
        clearInterval(temporizador)
      }
    }

    actualizar()
    iniciar()
    document.addEventListener('visibilitychange', alCambiarVisibilidad)
    return () => {
      clearInterval(temporizador)
      document.removeEventListener('visibilitychange', alCambiarVisibilidad)
    }
  }, [actualizar, intervalo])
}
