import { cx } from '../../../utils/cx'
import { iniciales } from '../../../utils/iniciales'
import styles from './Avatar.module.css'

/** Foto del usuario o, si no tiene, sus iniciales. */
export function Avatar({ nombre, foto, size = 'md', tone = 'primary' }) {
  return (
    <span className={cx(styles.avatar, styles[size], styles[tone])} aria-hidden="true">
      {foto ? <img src={foto} alt="" className={styles.img} /> : iniciales(nombre)}
    </span>
  )
}
