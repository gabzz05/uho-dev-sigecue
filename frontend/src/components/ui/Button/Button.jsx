import { Loader2 } from 'lucide-react'
import { cx } from '../../../utils/cx'
import styles from './Button.module.css'

/**
 * Botón del sistema de diseño.
 * `as` permite renderizarlo como otro componente (p. ej. `Link` de react-router).
 */
export function Button({
  as: Componente = 'button',
  variant = 'primary',
  size = 'md',
  icon: Icono,
  loading = false,
  fullWidth = false,
  disabled,
  className,
  children,
  type,
  ...props
}) {
  const esBoton = Componente === 'button'
  return (
    <Componente
      className={cx(styles.button, styles[variant], styles[size], fullWidth && styles.fullWidth, className)}
      type={esBoton ? (type ?? 'button') : type}
      disabled={esBoton ? disabled || loading : undefined}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <Loader2 className={styles.spinner} aria-hidden="true" />
      ) : (
        Icono && <Icono className={styles.icon} aria-hidden="true" />
      )}
      {children}
    </Componente>
  )
}
