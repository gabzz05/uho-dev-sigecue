import { NavLink } from 'react-router'
import { useAuth } from '../../../hooks/useAuth'
import { cx } from '../../../utils/cx'
import { Logo } from '../Logo/Logo'
import { menuVisible } from './menuAdmin'
import styles from './Sidebar.module.css'

/** Navegación lateral del panel. `badges`: contadores por path, p. ej. `{ solicitudes: 47 }`. */
export function Sidebar({ id, abierto, onNavegar, badges = {} }) {
  const { tienePermiso } = useAuth()
  const secciones = menuVisible(tienePermiso)

  return (
    <aside id={id} className={cx(styles.sidebar, abierto && styles.abierto)}>
      <div className={styles.logo}>
        <Logo to="/admin" subtitle="Panel administrativo" />
      </div>
      <nav aria-label="Menú principal">
        {secciones.map((seccion) => (
          <div key={seccion.titulo} className={styles.section}>
            <h2 className={styles.sectionTitle}>{seccion.titulo}</h2>
            <ul className={styles.list}>
              {seccion.items.map(({ path, label, icon: Icono }) => (
                <li key={path}>
                  <NavLink
                    to={path ? `/admin/${path}` : '/admin'}
                    end={!path}
                    className={({ isActive }) => cx(styles.item, isActive && styles.active)}
                    onClick={onNavegar}
                  >
                    <Icono className={styles.icon} aria-hidden="true" />
                    <span>{label}</span>
                    {badges[path] > 0 && <span className={styles.badge}>{badges[path]}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}
