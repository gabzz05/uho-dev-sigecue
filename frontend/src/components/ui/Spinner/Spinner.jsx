import { Loader2 } from 'lucide-react'
import { cx } from '../../../utils/cx'
import styles from './Spinner.module.css'

export function Spinner({ label = 'Cargando', fullPage = false }) {
  return (
    <div className={cx(styles.spinner, fullPage && styles.fullPage)} role="status">
      <Loader2 className={styles.icon} aria-hidden="true" />
      <span className={styles.label}>{label}…</span>
    </div>
  )
}
