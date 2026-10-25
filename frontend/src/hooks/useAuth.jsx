import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { seguirActividad } from '../services/actividad'
import { onSesionExpirada } from '../services/api'
import * as authService from '../services/auth'

const AuthContext = createContext(null)

export const ROL_ASPIRANTE = 'aspirante'

/**
 * Estado de la sesión para toda la app.
 * `estado`: 'cargando' (comprobando la cookie al arrancar) | 'autenticado' | 'anonimo'.
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [estado, setEstado] = useState('cargando')
  const [sesionExpirada, setSesionExpirada] = useState(false)

  useEffect(() => seguirActividad(), [])

  useEffect(() => {
    onSesionExpirada(() => {
      setUsuario(null)
      setEstado('anonimo')
      setSesionExpirada(true)
    })
    let vigente = true
    authService.restaurarSesion().then((perfil) => {
      if (!vigente) return
      setUsuario(perfil)
      setEstado(perfil ? 'autenticado' : 'anonimo')
    })
    return () => {
      vigente = false
    }
  }, [])

  const iniciarSesion = useCallback(async (identificador, password) => {
    const perfil = await authService.iniciarSesion(identificador, password)
    setUsuario(perfil)
    setEstado('autenticado')
    setSesionExpirada(false)
    return perfil
  }, [])

  const cerrarSesion = useCallback(async () => {
    try {
      await authService.cerrarSesion()
    } finally {
      setUsuario(null)
      setEstado('anonimo')
    }
  }, [])

  const tienePermiso = useCallback(
    (codigo) => Boolean(usuario?.permisos?.includes('*') || usuario?.permisos?.includes(codigo)),
    [usuario],
  )

  const valor = useMemo(
    () => ({
      usuario,
      estado,
      sesionExpirada,
      esAspirante: usuario?.rol?.codigo === ROL_ASPIRANTE,
      iniciarSesion,
      cerrarSesion,
      tienePermiso,
      actualizarUsuario: setUsuario,
    }),
    [usuario, estado, sesionExpirada, iniciarSesion, cerrarSesion, tienePermiso],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return contexto
}

/** Ruta de inicio según el tipo de usuario. */
// eslint-disable-next-line react/only-export-components
export function rutaDeInicio(usuario) {
  return usuario?.rol?.codigo === ROL_ASPIRANTE ? '/aspirante' : '/admin'
}
