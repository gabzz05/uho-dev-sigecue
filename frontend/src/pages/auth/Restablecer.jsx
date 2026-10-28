import { KeyRound } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { AuthCard } from '../../components/layout/AuthCard/AuthCard'
import { Alert, Button, Input } from '../../components/ui'
import { useFormulario } from '../../hooks/useFormulario'
import { restablecerPassword } from '../../services/auth'
import { validarPassword } from '../../utils/validaciones'
import styles from './auth.module.css'

/** Destino del enlace del correo de recuperación: elegir la contraseña nueva. */
export function Restablecer() {
  const [params] = useSearchParams()
  const uid = params.get('uid')
  const token = params.get('token')
  const navigate = useNavigate()
  const { campo, errorGeneral, enviando, enviar } = useFormulario({ password: '', confirmacion: '' })

  if (!uid || !token) {
    return (
      <AuthCard title="Restablecer contraseña">
        <div className={styles.center}>
          <Alert tone="danger">El enlace para restablecer la contraseña no es válido.</Alert>
          <Button as={Link} to="/recuperar" variant="secondary">
            Pedir un enlace nuevo
          </Button>
        </div>
      </AuthCard>
    )
  }

  async function alEnviar(evento) {
    evento.preventDefault()
    const mensaje = await enviar(
      ({ password }) => restablecerPassword(uid, token, password),
      ({ password, confirmacion }) => validarPassword(password, confirmacion),
    )
    if (mensaje) navigate('/login', { replace: true, state: { mensaje } })
  }

  return (
    <AuthCard
      title="Restablecer contraseña"
      subtitle="Elige la contraseña nueva de tu cuenta."
      footer={<Link to="/recuperar">Pedir un enlace nuevo</Link>}
    >
      <form className={styles.form} onSubmit={alEnviar} noValidate>
        {errorGeneral && <Alert tone="danger">{errorGeneral}</Alert>}
        <Input label="Contraseña nueva" type="password" autoComplete="new-password" required {...campo('password')} />
        <Input label="Repite la contraseña" type="password" autoComplete="new-password" required {...campo('confirmacion')} />
        <Button type="submit" icon={KeyRound} loading={enviando} fullWidth>
          Cambiar contraseña
        </Button>
      </form>
    </AuthCard>
  )
}
