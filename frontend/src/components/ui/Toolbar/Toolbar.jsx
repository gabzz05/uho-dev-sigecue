import { cx } from '../../../utils/cx'
import styles from './Toolbar.module.css'

/** Barra de filtros sobre una tabla. Los hijos se reparten y se apilan en pantallas estrechas. */
export function Toolbar({ className, children }) {
  return <div className={cx(styles.toolbar, className)}>{children}</div>
}
