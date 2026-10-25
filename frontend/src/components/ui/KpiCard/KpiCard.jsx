import { cx } from '../../../utils/cx'
import styles from './KpiCard.module.css'

/** Indicador numérico del dashboard: etiqueta, valor y una línea de contexto opcional. */
export function KpiCard({ label, value, hint, icon: Icono, tone = 'primary' }) {
  return (
    <article className={styles.kpi}>
      <div className={styles.top}>
        <span className={styles.label}>{label}</span>
        {Icono && (
          <span className={cx(styles.icon, styles[tone])} aria-hidden="true">
            <Icono />
          </span>
        )}
      </div>
      <strong className={cx(styles.value, styles[`text-${tone}`])}>{value}</strong>
      {hint && <span className={styles.hint}>{hint}</span>}
    </article>
  )
}
