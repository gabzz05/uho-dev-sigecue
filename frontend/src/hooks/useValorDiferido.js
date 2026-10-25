import { useEffect, useState } from 'react'

/** Devuelve `valor` cuando lleva `ms` sin cambiar (p. ej. para no buscar con cada tecla). */
export function useValorDiferido(valor, ms) {
  const [diferido, setDiferido] = useState(valor)

  useEffect(() => {
    const espera = setTimeout(() => setDiferido(valor), ms)
    return () => clearTimeout(espera)
  }, [valor, ms])

  return diferido
}
