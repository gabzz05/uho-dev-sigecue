import { cx } from '../../../utils/cx'
import styles from './Card.module.css'

export function Card({ as: Componente = 'section', className, children, ...props }) {
  return (
    <Componente className={cx(styles.card, className)} {...props}>
      {children}
    </Componente>
  )
}

export function CardHeader({ title, actions, className }) {
  return (
    <header className={cx(styles.header, className)}>
      <h3 className={styles.title}>{title}</h3>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  )
}

export function CardBody({ className, children }) {
  return <div className={cx(styles.body, className)}>{children}</div>
}

export function CardFooter({ className, children }) {
  return <footer className={cx(styles.footer, className)}>{children}</footer>
}
