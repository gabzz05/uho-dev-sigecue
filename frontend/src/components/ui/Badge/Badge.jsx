import { cx } from '../../../utils/cx'
import styles from './Badge.module.css'

/** Etiqueta compacta para estados, entidades o valores destacados. */
export function Badge({ tone = 'neutral', className, children, ...props }) {
  return (
    <span className={cx(styles.badge, styles[tone], className)} {...props}>
      {children}
    </span>
  )
}

/**
 * Badge para el estado de un registro del backend.
 * Cada módulo define su mapa: `{ pendiente: { label: 'Pendiente', tone: 'warning' } }`.
 */
export function StatusBadge({ estado, mapa }) {
  const { label = estado, tone = 'neutral' } = mapa[estado] ?? {}
  return <Badge tone={tone}>{label}</Badge>
}
