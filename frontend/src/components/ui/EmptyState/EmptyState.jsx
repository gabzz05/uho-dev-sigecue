import { Inbox } from 'lucide-react'
import styles from './EmptyState.module.css'

export function EmptyState({ icon: Icono = Inbox, title, message, action }) {
  return (
    <div className={styles.empty}>
      <Icono className={styles.icon} aria-hidden="true" />
      {title && <strong className={styles.title}>{title}</strong>}
      {message && <p className={styles.message}>{message}</p>}
      {action}
    </div>
  )
}
