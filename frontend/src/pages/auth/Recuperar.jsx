import { Mail } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { AuthCard } from '../../components/layout/AuthCard/AuthCard'
import { Alert, Button, Input } from '../../components/ui'
import { useFormulario } from '../../hooks/useFormulario'
import { pedirRecuperacion } from '../../services/auth'
import { PATRON_EMAIL } from '../../utils/validaciones'
import styles from './auth.module.css'

function validar({ email }) {
  return PATRON_EMAIL.test(email) ? {} : { email: 'Escribe un correo electrónico válido.' }
}

/** Pide por correo el enlace para restablecer la contraseña. */
export function Recuperar() {
  const { campo, errorGeneral, enviando, enviar } = useFormulario({ email: '' })
  const [mensaje, setMensaje] = useState('')

  async function alEnviar(evento) {
    evento.preventDefault()
    const resultado = await enviar(({ email }) => pedirRecuperacion(email.trim()), validar)
    if (resultado) setMensaje(resultado)
  }

  if (mensaje) {
    return (
      <AuthCard title="Revisa tu correo">
        <div className={styles.center}>
          <Alert tone="success">{mensaje}</Alert>
          <Button as={Link} to="/login" variant="secondary">
            Volver a iniciar sesión
          </Button>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Recuperar contraseña"
      subtitle="Escribe el correo de tu cuenta y te enviaremos un enlace para elegir una contraseña nueva."
      footer={<Link to="/login">Volver a iniciar sesión</Link>}
    >
      <form className={styles.form} onSubmit={alEnviar} noValidate>
        {errorGeneral && <Alert tone="danger">{errorGeneral}</Alert>}
        <Input label="Correo electrónico" type="email" autoComplete="email" required {...campo('email')} />
        <Button type="submit" icon={Mail} loading={enviando} fullWidth>
          Enviar enlace
        </Button>
      </form>
    </AuthCard>
  )
}
