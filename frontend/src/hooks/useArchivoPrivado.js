import { useEffect, useState } from 'react'
import { obtenerArchivo } from '../services/aspirante'

/**
 * URL `blob:` de un archivo privado de la API (foto, documento).
 * Un `<img>` no puede enviar el token, así que se descarga con el cliente
 * HTTP y se libera al cambiar la ruta o desmontar. `null` mientras carga,
 * si no hay ruta o si falla.
 */
export function useArchivoPrivado(ruta) {
  const [archivo, setArchivo] = useState({ ruta: null, url: null })

  useEffect(() => {
    if (!ruta) return undefined
    let vigente = true
    let url = null
    obtenerArchivo(ruta)
      .then((blob) => {
        if (!vigente) return
        url = URL.createObjectURL(blob)
        setArchivo({ ruta, url })
      })
      .catch(() => vigente && setArchivo({ ruta, url: null }))
    return () => {
      vigente = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [ruta])

  // Derivado: si la ruta cambió y aún no llegó el archivo nuevo, no se muestra el anterior.
  return ruta && archivo.ruta === ruta ? archivo.url : null
}
