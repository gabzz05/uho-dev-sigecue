import { useState } from 'react'
import { cx } from '../../../utils/cx'
import { iniciales } from '../../../utils/iniciales'
import styles from './Avatar.module.css'

/** Foto del usuario o, si no tiene o no carga, sus iniciales. */
export function Avatar({ nombre, foto, size = 'md', tone = 'primary' }) {
  const [fallida, setFallida] = useState(null)
  const mostrarFoto = foto && fallida !== foto

  return (
    <span className={cx(styles.avatar, styles[size], styles[tone])} aria-hidden="true">
      {mostrarFoto ? <img src={foto} alt="" className={styles.img} onError={() => setFallida(foto)} /> : iniciales(nombre)}
    </span>
  )
}
