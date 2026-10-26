import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { notificaciones } from '../services/notificaciones'

export const INTERVALO_POLLING_MS = 60_000

const NotificacionesContext = createContext(null)

/**
 * Contador de notificaciones no leídas para la campana (RF-073).
 * Consulta cada 60 s y solo con la pestaña visible; al volver a la pestaña
 * consulta enseguida. El polling no renueva la sesión por sí solo: eso
 * depende de la actividad del usuario (ver services/actividad.js).
 */
export function NotificacionesProvider({ children }) {
  const [noLeidas, setNoLeidas] = useState(0)

  const actualizar = useCallback(() => {
    notificaciones.noLeidas().then(setNoLeidas, () => {})
  }, [])

  useEffect(() => {
    let intervalo = null
    function iniciar() {
      clearInterval(intervalo)
      intervalo = setInterval(actualizar, INTERVALO_POLLING_MS)
    }
    function alCambiarVisibilidad() {
      if (document.visibilityState === 'visible') {
        actualizar()
        iniciar()
      } else {
        clearInterval(intervalo)
      }
    }

    actualizar()
    iniciar()
    document.addEventListener('visibilitychange', alCambiarVisibilidad)
    return () => {
      clearInterval(intervalo)
      document.removeEventListener('visibilitychange', alCambiarVisibilidad)
    }
  }, [actualizar])

  const valor = useMemo(() => ({ noLeidas, actualizar }), [noLeidas, actualizar])
  return <NotificacionesContext.Provider value={valor}>{children}</NotificacionesContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useNotificaciones() {
  return useContext(NotificacionesContext) ?? { noLeidas: 0, actualizar: () => {} }
}
