import { LogIn } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { AuthCard } from '../../components/layout/AuthCard/AuthCard'
import { Alert, Button, Input } from '../../components/ui'
import { rutaDeInicio, useAuth } from '../../hooks/useAuth'
import { useFormulario } from '../../hooks/useFormulario'
import styles from './auth.module.css'

function validar({ identificador, password }) {
  const errores = {}
  if (!identificador.trim()) errores.identificador = 'Escribe tu correo o tu usuario.'
  if (!password) errores.password = 'Escribe tu contraseña.'
  return errores
}

export function Login() {
  const { usuario, iniciarSesion, sesionExpirada } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { campo, errorGeneral, enviando, enviar } = useFormulario({ identificador: '', password: '' })

  if (usuario) return <Navigate to={rutaDeInicio(usuario)} replace />

  async function alEnviar(evento) {
    evento.preventDefault()
    const perfil = await enviar(({ identificador, password }) => iniciarSesion(identificador, password), validar)
    if (perfil) navigate(location.state?.desde ?? rutaDeInicio(perfil), { replace: true })
  }

  return (
    <AuthCard
      title="Iniciar sesión"
      subtitle="Aspirantes: entra con tu correo. Personal de la UHO: con tu usuario."
      footer={
        <>
          ¿Aún no tienes cuenta? <Link to="/registro">Regístrate como aspirante</Link>
        </>
      }
    >
      <form className={styles.form} onSubmit={alEnviar} noValidate>
        {sesionExpirada && !errorGeneral && (
          <Alert tone="warning">Tu sesión caducó por inactividad. Vuelve a iniciar sesión.</Alert>
        )}
        {location.state?.mensaje && !errorGeneral && <Alert tone="success">{location.state.mensaje}</Alert>}
        {errorGeneral && <Alert tone="danger">{errorGeneral}</Alert>}
        <Input label="Correo o usuario" autoComplete="username" required {...campo('identificador')} />
        <Input label="Contraseña" type="password" autoComplete="current-password" required {...campo('password')} />
        <Link to="/recuperar" className={styles.enlace}>
          ¿Olvidaste tu contraseña?
        </Link>
        <Button type="submit" icon={LogIn} loading={enviando} fullWidth>
          Entrar
        </Button>
      </form>
    </AuthCard>
  )
}
