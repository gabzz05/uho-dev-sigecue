import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../services/errores'
import { useValorDiferido } from './useValorDiferido'

const ESPERA_BUSQUEDA_MS = 300

function parametros(filtros) {
  return Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v !== undefined && v !== null))
}

/**
 * Listado paginado y filtrado de un recurso de la API.
 * Cambiar un filtro vuelve a la página 1. La búsqueda de texto (`buscar`)
 * espera a que el usuario deje de escribir.
 */
export function useListado(recurso, { filtrosIniciales = {}, pageSize = 20 } = {}) {
  const [filtros, setFiltros] = useState(filtrosIniciales)
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState({ count: 0, results: [] })
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  // Clave de la última consulta terminada: se está cargando mientras no coincide con la actual.
  const [cargada, setCargada] = useState(null)

  const buscar = useValorDiferido(filtros.buscar ?? '', ESPERA_BUSQUEDA_MS)
  const consulta = JSON.stringify(parametros({ ...filtros, buscar }))
  const clave = `${recurso.ruta}|${consulta}|${pagina}|${pageSize}|${version}`

  useEffect(() => {
    let vigente = true
    recurso
      .listar({ ...JSON.parse(consulta), page: pagina, page_size: pageSize })
      .then((respuesta) => {
        if (!vigente) return
        setDatos(respuesta)
        setError('')
      })
      .catch((err) => vigente && setError(mensajeDeError(err)))
      .finally(() => vigente && setCargada(clave))
    return () => {
      vigente = false
    }
  }, [recurso, consulta, pagina, pageSize, clave])

  const cargando = cargada !== clave

  const cambiarFiltro = useCallback((nombre, valor) => {
    setFiltros((f) => ({ ...f, [nombre]: valor }))
    setPagina(1)
  }, [])

  const recargar = useCallback(() => setVersion((v) => v + 1), [])

  return {
    filas: datos.results,
    total: datos.count,
    pagina,
    pageSize,
    setPagina,
    filtros,
    cambiarFiltro,
    cargando,
    error,
    recargar,
  }
}
