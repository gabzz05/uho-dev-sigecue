import { Link } from 'react-router'
import { useIdentidad } from '../../../hooks/useIdentidad'
import { cx } from '../../../utils/cx'
import styles from './Logo.module.css'

/** Marca del sistema: el escudo de la identidad visual o, si no hay, el distintivo "UHO". */
export function Logo({ to = '/', subtitle, compact = false }) {
  const { identidad } = useIdentidad()
  const institucion = identidad.nombre_institucion

  return (
    <Link to={to} className={styles.logo} aria-label={`SIGECUE — ${institucion}, ir al inicio`}>
      {identidad.escudo ? (
        <img src={identidad.escudo} alt="" className={styles.escudo} />
      ) : (
        <span className={styles.mark} aria-hidden="true">
          UHO
        </span>
      )}
      <span className={cx(styles.text, compact && styles.compact)}>
        <strong className={styles.name}>SIGECUE</strong>
        <span className={styles.subtitle}>{subtitle ?? institucion}</span>
      </span>
    </Link>
  )
}
