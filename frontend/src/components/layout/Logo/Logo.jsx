import { Link } from 'react-router'
import { cx } from '../../../utils/cx'
import styles from './Logo.module.css'

/** Marca del sistema. El escudo oficial de la UHO sustituirá al distintivo cuando esté disponible. */
export function Logo({ to = '/', subtitle = 'Universidad de Holguín', compact = false }) {
  return (
    <Link to={to} className={styles.logo} aria-label="SIGECUE — Universidad de Holguín, ir al inicio">
      <span className={styles.mark} aria-hidden="true">
        UHO
      </span>
      <span className={cx(styles.text, compact && styles.compact)}>
        <strong className={styles.name}>SIGECUE</strong>
        <span className={styles.subtitle}>{subtitle}</span>
      </span>
    </Link>
  )
}
