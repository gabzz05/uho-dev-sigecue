import { Outlet } from 'react-router'
import { Logo } from '../Logo/Logo'
import { NotificationBell } from '../NotificationBell/NotificationBell'
import { UserMenu } from '../UserMenu/UserMenu'
import styles from './AspiranteLayout.module.css'

/** Estructura del portal del aspirante: cabecera y contenido centrado. */
export function AspiranteLayout() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <Logo to="/aspirante" subtitle="Portal del Aspirante" compact />
        <div className={styles.right}>
          <NotificationBell inverse />
          <UserMenu inverse perfilPath="/aspirante/perfil" />
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
