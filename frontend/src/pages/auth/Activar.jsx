import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { AuthCard } from '../../components/layout/AuthCard/AuthCard'
import { Alert, Button, Spinner } from '../../components/ui'
import { activarCuenta } from '../../services/auth'
import { mensajeDeError } from '../../services/errores'
import styles from './auth.module.css'

/** Destino del enlace del correo de activación (RF-045). */
export function Activar() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const [resultado, setResultado] = useState(token ? null : { ok: false, mensaje: 'El enlace de activación no es válido.' })

  useEffect(() => {
    if (!token) return undefined
    let vigente = true
    activarCuenta(token)
      .then((mensaje) => vigente && setResultado({ ok: true, mensaje }))
      .catch((error) => vigente && setResultado({ ok: false, mensaje: mensajeDeError(error) }))
    return () => {
      vigente = false
    }
  }, [token])

  return (
    <AuthCard title="Activación de cuenta">
      <div className={styles.center}>
        {!resultado ? (
          <Spinner label="Activando tu cuenta" />
        ) : (
          <>
            <Alert tone={resultado.ok ? 'success' : 'danger'}>{resultado.mensaje}</Alert>
            {resultado.ok ? (
              <Button as={Link} to="/login">
                Iniciar sesión
              </Button>
            ) : (
              <Button as={Link} to="/registro" variant="secondary">
                Volver al registro
              </Button>
            )}
          </>
        )}
      </div>
    </AuthCard>
  )
}
