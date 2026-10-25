import { useEffect, useState } from 'react'
import { mensajeDeError } from '../services/errores'

/** Carga unos datos al montar el componente. `cargar` debe ser estable (definida fuera o con useCallback). */
export function useCarga(cargar) {
  const [estado, setEstado] = useState({ datos: null, error: '', cargando: true })

  useEffect(() => {
    let vigente = true
    cargar()
      .then((datos) => vigente && setEstado({ datos, error: '', cargando: false }))
      .catch((error) => vigente && setEstado({ datos: null, error: mensajeDeError(error), cargando: false }))
    return () => {
      vigente = false
    }
  }, [cargar])

  return estado
}
