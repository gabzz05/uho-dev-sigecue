import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { obtenerIdentidad } from '../services/configuracion'

const IdentidadContext = createContext(null)

// Campo de la identidad → variable CSS de tokens.css que sobrescribe.
const VARIABLES = {
  color_primario: '--color-primary',
  color_primario_claro: '--color-primary-light',
  color_acento: '--color-accent',
}

const POR_DEFECTO = { nombre_institucion: 'Universidad de Holguín', escudo: null }

function aplicarColores(identidad) {
  const raiz = document.documentElement.style
  Object.entries(VARIABLES).forEach(([campo, variable]) => {
    if (identidad[campo]) raiz.setProperty(variable, identidad[campo])
  })
}

/**
 * Identidad visual guardada en la base de datos (RE-001). Al arrancar la pide
 * a la API y sobrescribe los colores de tokens.css. Si la API no responde, la
 * app sigue con los valores por defecto de tokens.css.
 */
export function IdentidadProvider({ children }) {
  const [identidad, setIdentidad] = useState(POR_DEFECTO)

  const actualizar = useCallback((nueva) => {
    aplicarColores(nueva)
    setIdentidad(nueva)
  }, [])

  useEffect(() => {
    let vigente = true
    obtenerIdentidad()
      .then((datos) => vigente && actualizar(datos))
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [actualizar])

  const valor = useMemo(() => ({ identidad, actualizar }), [identidad, actualizar])
  return <IdentidadContext.Provider value={valor}>{children}</IdentidadContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useIdentidad() {
  return useContext(IdentidadContext) ?? { identidad: POR_DEFECTO, actualizar: () => {} }
}
