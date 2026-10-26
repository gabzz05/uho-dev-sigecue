import styles from './VisuallyHidden.module.css'

/** Texto solo para lectores de pantalla (p. ej. el encabezado de una columna de acciones). */
export function VisuallyHidden({ children }) {
  return <span className={styles.oculto}>{children}</span>
}
