import { NavLink, Outlet } from 'react-router'
import { NotificacionesProvider } from '../../../hooks/useNotificaciones'
import { Logo } from '../Logo/Logo'
import { NotificationCenter } from '../NotificationCenter/NotificationCenter'
import { UserMenu } from '../UserMenu/UserMenu'
import styles from './AspiranteLayout.module.css'

const SECCIONES = [
  { to: '/aspirante', label: 'Inicio', end: true },
  { to: '/aspirante/completar-perfil', label: 'Mi perfil de aspirante' },
  { to: '/aspirante/solicitud', label: 'Mi solicitud' },
  { to: '/aspirante/prematricula', label: 'Prematrícula' },
]

/** Estructura del portal del aspirante: cabecera, secciones y contenido centrado. */
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
        <nav className={styles.nav} aria-label="Portal del aspirante">
          {SECCIONES.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? `${styles.link} ${styles.activo}` : styles.link)}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </NotificacionesProvider>
  )
}
