import { ChevronDown, LogOut, UserRound } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../../../hooks/useAuth'
import { cx } from '../../../utils/cx'
import { Avatar } from '../../ui'
import styles from './UserMenu.module.css'

/** Chip del usuario con menú desplegable (perfil y cerrar sesión). */
export function UserMenu({ inverse = false, perfilPath }) {
  const { usuario, cerrarSesion } = useAuth()
  const [abierto, setAbierto] = useState(false)
  const contenedor = useRef(null)
  const menuId = useId()
  const navigate = useNavigate()

  useEffect(() => {
    if (!abierto) return undefined
    function alClicFuera(evento) {
      if (!contenedor.current?.contains(evento.target)) setAbierto(false)
    }
    function alTeclear(evento) {
      if (evento.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('mousedown', alClicFuera)
    document.addEventListener('keydown', alTeclear)
    return () => {
      document.removeEventListener('mousedown', alClicFuera)
      document.removeEventListener('keydown', alTeclear)
    }
  }, [abierto])

  if (!usuario) return null
  const nombre = `${usuario.nombre} ${usuario.apellidos}`.trim() || usuario.username

  async function salir() {
    setAbierto(false)
    await cerrarSesion()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.wrapper} ref={contenedor}>
      <button
        type="button"
        className={cx(styles.chip, inverse && styles.inverse)}
        aria-expanded={abierto}
        aria-controls={menuId}
        onClick={() => setAbierto((a) => !a)}
      >
        <Avatar nombre={nombre} foto={usuario.foto} size="sm" tone={inverse ? 'accent' : 'primary'} />
        <span className={styles.texts}>
          <span className={styles.name}>{nombre}</span>
          <span className={styles.role}>{usuario.rol?.nombre ?? 'Superadmin'}</span>
        </span>
        <ChevronDown className={styles.chevron} aria-hidden="true" />
      </button>
      {abierto && (
        <ul id={menuId} className={styles.menu}>
          {perfilPath && (
            <li>
              <Link to={perfilPath} className={styles.item} onClick={() => setAbierto(false)}>
                <UserRound aria-hidden="true" /> Mi perfil
              </Link>
            </li>
          )}
          <li>
            <button type="button" className={styles.item} onClick={salir}>
              <LogOut aria-hidden="true" /> Cerrar sesión
            </button>
          </li>
        </ul>
      )}
    </div>
  )
}
