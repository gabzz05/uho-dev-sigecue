import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { cx } from '../../../utils/cx'
import styles from './Alert.module.css'

const ICONOS = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: XCircle }

/** Aviso en línea. `warning` y `danger` se anuncian de inmediato a lectores de pantalla. */
export function Alert({ tone = 'info', title, action, onClose, className, children }) {
  const Icono = ICONOS[tone]
  const urgente = tone === 'warning' || tone === 'danger'
  return (
    <div className={cx(styles.alert, styles[tone], className)} role={urgente ? 'alert' : 'status'}>
      <Icono className={styles.icon} aria-hidden="true" />
      <div className={styles.content}>
        {title && <strong className={styles.title}>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
      {action && <div className={styles.action}>{action}</div>}
      {onClose && (
        <button type="button" className={styles.close} onClick={onClose} aria-label="Cerrar aviso">
          <X aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
