import { Bell } from 'lucide-react'
import { cx } from '../../../utils/cx'
import styles from './NotificationBell.module.css'

/** Campana con el número de notificaciones no leídas (RF-073). Se conecta en feature/notifications. */
export function NotificationBell({ count = 0, onClick, inverse = false }) {
  const etiqueta = count > 0 ? `Notificaciones: ${count} sin leer` : 'Notificaciones'
  return (
    <button type="button" className={cx(styles.bell, inverse && styles.inverse)} aria-label={etiqueta} onClick={onClick}>
      <Bell aria-hidden="true" />
      {count > 0 && (
        <span className={styles.badge} aria-hidden="true">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </button>
  )
}
