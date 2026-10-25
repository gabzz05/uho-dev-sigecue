import { ShieldX } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { rutaDeInicio, useAuth } from '../../../hooks/useAuth'
import { EmptyState, Spinner } from '../../ui'

/**
 * Protege un grupo de rutas.
 * - `tipo`: 'interno' (panel) o 'aspirante' (portal). Si no coincide, redirige al inicio que le toca.
 * - `permiso`: código `modulo.accion` requerido; si falta, muestra un aviso.
 * La API valida igualmente cada petición: esto solo evita mostrar pantallas inútiles.
 */
export function RequireAuth({ tipo, permiso, children }) {
  const { estado, usuario, esAspirante, tienePermiso } = useAuth()
  const location = useLocation()

  if (estado === 'cargando') return <Spinner label="Comprobando tu sesión" fullPage />
  if (!usuario) return <Navigate to="/login" replace state={{ desde: location.pathname }} />

  const tipoUsuario = esAspirante ? 'aspirante' : 'interno'
  if (tipo && tipo !== tipoUsuario) return <Navigate to={rutaDeInicio(usuario)} replace />
  if (permiso && !tienePermiso(permiso)) {
    return (
      <EmptyState
        icon={ShieldX}
        title="No tienes permiso para ver esta sección"
        message="Si crees que deberías tener acceso, contacta con el administrador del sistema."
      />
    )
  }

  return children ?? <Outlet />
}
