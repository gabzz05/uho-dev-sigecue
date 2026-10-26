import { useCallback, useState } from 'react'
import { erroresDeCampo, mensajeDeError } from '../services/errores'

/**
 * Estado de un formulario: valores, errores por campo, error general y envío.
 * `enviar(accion)` ejecuta la acción y traduce los errores de la API.
 */
export function useFormulario(valoresIniciales) {
  const [valores, setValores] = useState(valoresIniciales)
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  const campo = useCallback(
    (nombre) => ({
      name: nombre,
      value: valores[nombre],
      error: errores[nombre],
      onChange: (evento) => {
        const { type, checked, value } = evento.target
        setValores((v) => ({ ...v, [nombre]: type === 'checkbox' ? checked : value }))
        setErrores((e) => (e[nombre] ? { ...e, [nombre]: undefined } : e))
      },
    }),
    [valores, errores],
  )

  const checkbox = useCallback(
    (nombre) => {
      const { value, ...resto } = campo(nombre)
      return { ...resto, checked: Boolean(value) }
    },
    [campo],
  )

  /** `validar` devuelve errores locales `{campo: mensaje}`; si hay alguno no se llama a la API. */
  const enviar = useCallback(
    async (accion, validar) => {
      const locales = validar?.(valores) ?? {}
      if (Object.keys(locales).length > 0) {
        setErrores(locales)
        return undefined
      }
      setEnviando(true)
      setErrorGeneral('')
      setErrores({})
      try {
        return await accion(valores)
      } catch (error) {
        setErrores(erroresDeCampo(error))
        setErrorGeneral(mensajeDeError(error))
        return undefined
      } finally {
        setEnviando(false)
      }
    },
    [valores],
  )

  return { valores, campo, checkbox, errores, setErrores, errorGeneral, enviando, enviar, setValores }
}
