import { cx } from '../../../utils/cx'
import styles from './Avatar.module.css'

export function iniciales(nombre = '') {
  return nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')
}

/** Foto del usuario o, si no tiene, sus iniciales. */
export function Avatar({ nombre, foto, size = 'md', tone = 'primary' }) {
  return (
    <span className={cx(styles.avatar, styles[size], styles[tone])} aria-hidden="true">
      {foto ? <img src={foto} alt="" className={styles.img} /> : iniciales(nombre)}
    </span>
  )
}
