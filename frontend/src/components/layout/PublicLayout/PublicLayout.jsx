import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { rutaDeInicio, useAuth } from '../../../hooks/useAuth'
import { cx } from '../../../utils/cx'
import { Button } from '../../ui'
import { Logo } from '../Logo/Logo'
import styles from './PublicLayout.module.css'

const ENLACES = [
  { to: '/#carreras', label: 'Carreras' },
  { to: '/resultados', label: 'Resultados' },
]

/** Estructura de las páginas públicas: cabecera institucional, contenido y pie. */
export function PublicLayout() {
  const { usuario } = useAuth()
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <Logo compact />
        <button
          type="button"
          className={styles.menuButton}
          aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
          aria-expanded={menuAbierto}
          aria-controls="nav-publica"
          onClick={() => setMenuAbierto((a) => !a)}
        >
          {menuAbierto ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <nav id="nav-publica" className={cx(styles.nav, menuAbierto && styles.navAbierta)} aria-label="Navegación pública">
          {ENLACES.map((enlace) => (
            <NavLink key={enlace.to} to={enlace.to} className={styles.link} onClick={() => setMenuAbierto(false)}>
              {enlace.label}
            </NavLink>
          ))}
          {usuario ? (
            <Button as={Link} to={rutaDeInicio(usuario)} variant="accent" size="sm">
              Mi panel
            </Button>
          ) : (
            <Button as={Link} to="/login" variant="accent" size="sm">
              Iniciar sesión
            </Button>
          )}
        </nav>
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <p>
          <strong>Universidad de Holguín</strong> · SIGECUE — Sistema de Gestión de Carreras por Encuentro
        </p>
        <p className={styles.footerMuted}>Dirección de Informatización</p>
      </footer>
    </div>
  )
}
