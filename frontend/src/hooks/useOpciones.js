import { useEffect, useRef, useState } from 'react'

const porNombre = (item) => item.nombre

/**
 * Opciones `{value, label, item}` para un <Select> a partir de un recurso de la API.
 * Pide hasta 100 elementos activos: pensado para catálogos cortos (municipios, áreas...).
 */
export function useOpciones(recurso, { etiqueta = porNombre, params = {} } = {}) {
  const [opciones, setOpciones] = useState([])
  // Una `etiqueta` inline cambia en cada render: no debe relanzar la petición.
  const etiquetaRef = useRef(etiqueta)
  useEffect(() => {
    etiquetaRef.current = etiqueta
  })
  const consulta = JSON.stringify({ page_size: 100, activo: true, ...params })

  useEffect(() => {
    if (!recurso) return undefined
    let vigente = true
    recurso
      .listar(JSON.parse(consulta))
      .then((datos) => {
        if (!vigente) return
        setOpciones(datos.results.map((item) => ({ value: String(item.id), label: etiquetaRef.current(item), item })))
      })
      .catch(() => vigente && setOpciones([]))
    return () => {
      vigente = false
    }
  }, [recurso, consulta])

  return opciones
}
