import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { notificaciones } from '../services/notificaciones'
import { usePolling } from './usePolling'

export { INTERVALO_POLLING_MS } from './usePolling'

const NotificacionesContext = createContext(null)

/**
 * Contador de notificaciones no leídas para la campana (RF-073).
 * Consulta cada 60 s con la pestaña visible (`usePolling`).
 */
export function NotificacionesProvider({ children }) {
  const [noLeidas, setNoLeidas] = useState(0)

  const actualizar = useCallback(() => {
    notificaciones.noLeidas().then(setNoLeidas, () => {})
  }, [])

  usePolling(actualizar)

  const valor = useMemo(() => ({ noLeidas, actualizar }), [noLeidas, actualizar])
  return <NotificacionesContext.Provider value={valor}>{children}</NotificacionesContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useNotificaciones() {
  return useContext(NotificacionesContext) ?? { noLeidas: 0, actualizar: () => {} }
}
