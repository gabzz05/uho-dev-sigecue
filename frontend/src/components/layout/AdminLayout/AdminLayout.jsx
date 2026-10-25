import { Menu } from 'lucide-react'
import { useState } from 'react'
import { Outlet } from 'react-router'
import { NotificationBell } from '../NotificationBell/NotificationBell'
import { Sidebar } from '../Sidebar/Sidebar'
import { UserMenu } from '../UserMenu/UserMenu'
import styles from './AdminLayout.module.css'

const SIDEBAR_ID = 'sidebar-admin'

/** Estructura del panel de roles internos: sidebar, barra superior y contenido. */
export function AdminLayout() {
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className={styles.layout}>
      <a href="#contenido" className={styles.skip}>
        Saltar al contenido
      </a>
      <Sidebar id={SIDEBAR_ID} abierto={menuAbierto} onNavegar={() => setMenuAbierto(false)} />
      {menuAbierto && <div className={styles.backdrop} onClick={() => setMenuAbierto(false)} aria-hidden="true" />}

      <div className={styles.main}>
        <header className={styles.topbar}>
          <button
            type="button"
            className={styles.menuButton}
            aria-label="Abrir menú"
            aria-expanded={menuAbierto}
            aria-controls={SIDEBAR_ID}
            onClick={() => setMenuAbierto(true)}
          >
            <Menu aria-hidden="true" />
          </button>
          <div className={styles.topbarRight}>
            <NotificationBell />
            <UserMenu perfilPath="/admin/perfil" />
          </div>
        </header>
        <main id="contenido" className={styles.content} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
