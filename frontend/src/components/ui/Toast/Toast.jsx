import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { Alert } from '../Alert/Alert'
import styles from './Toast.module.css'

const ToastContext = createContext(null)
const DURACION_MS = 5000

/** Confirmaciones breves tras una acción del usuario (RG-004). */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const siguienteId = useRef(0)

  const cerrar = useCallback((id) => setToasts((actuales) => actuales.filter((t) => t.id !== id)), [])

  const mostrar = useCallback(
    (mensaje, tone = 'success') => {
      const id = ++siguienteId.current
      setToasts((actuales) => [...actuales, { id, mensaje, tone }])
      setTimeout(() => cerrar(id), DURACION_MS)
    },
    [cerrar],
  )

  const api = useMemo(
    () => ({
      exito: (mensaje) => mostrar(mensaje, 'success'),
      error: (mensaje) => mostrar(mensaje, 'danger'),
      info: (mensaje) => mostrar(mensaje, 'info'),
    }),
    [mostrar],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className={styles.region}>
        {toasts.map((t) => (
          <Alert key={t.id} tone={t.tone} onClose={() => cerrar(t.id)} className={styles.toast}>
            {t.mensaje}
          </Alert>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useToast() {
  const contexto = useContext(ToastContext)
  if (!contexto) throw new Error('useToast debe usarse dentro de <ToastProvider>')
  return contexto
}
