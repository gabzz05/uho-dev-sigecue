import { Outlet } from 'react-router'
import { NotificacionesProvider } from '../../../hooks/useNotificaciones'
import { Logo } from '../Logo/Logo'
import { NotificationCenter } from '../NotificationCenter/NotificationCenter'
import { UserMenu } from '../UserMenu/UserMenu'
import styles from './AspiranteLayout.module.css'

/** Estructura del portal del aspirante: cabecera y contenido centrado. */
export function AspiranteLayout() {
  return (
    <NotificacionesProvider>
      <div className={styles.layout}>
        <header className={styles.header}>
          <Logo to="/aspirante" subtitle="Portal del Aspirante" compact />
          <div className={styles.right}>
            <NotificationCenter inverse verTodasPath="/aspirante/notificaciones" />
            <UserMenu inverse perfilPath="/aspirante/perfil" />
          </div>
        </header>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </NotificacionesProvider>
  )
}
