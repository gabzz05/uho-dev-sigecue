import styles from './AuthCard.module.css'

/** Tarjeta centrada para login, registro y activación. */
export function AuthCard({ title, subtitle, footer, wide = false, children }) {
  return (
    <div className={styles.page}>
      <section className={wide ? `${styles.card} ${styles.wide}` : styles.card} aria-labelledby="auth-titulo">
        <header className={styles.header}>
          <h1 id="auth-titulo" className={styles.title}>
            {title}
          </h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </header>
        <div className={styles.body}>{children}</div>
        {footer && <footer className={styles.footer}>{footer}</footer>}
      </section>
    </div>
  )
}
