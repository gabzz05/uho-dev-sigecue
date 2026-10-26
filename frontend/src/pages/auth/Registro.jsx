import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { AuthCard } from '../../components/layout/AuthCard/AuthCard'
import { Alert, Button, Checkbox, Input } from '../../components/ui'
import { useFormulario } from '../../hooks/useFormulario'
import { registrarAspirante } from '../../services/auth'
import styles from './auth.module.css'
import { datosDeRegistro, validarRegistro } from '../../utils/validaciones'

const INICIAL = {
  nombre: '',
  apellidos: '',
  ci: '',
  email: '',
  celular: '',
  password: '',
  confirmacion: '',
  acepta_privacidad: false,
}

export function Registro() {
  const { campo, checkbox, errorGeneral, enviando, enviar } = useFormulario(INICIAL)
  const [mensaje, setMensaje] = useState('')

  async function alEnviar(evento) {
    evento.preventDefault()
    const resultado = await enviar((v) => registrarAspirante(datosDeRegistro(v)), validarRegistro)
    if (resultado) setMensaje(resultado)
  }

  if (mensaje) {
    return (
      <AuthCard title="Revisa tu correo">
        <div className={styles.center}>
          <Alert tone="success">{mensaje}</Alert>
          <p>El enlace de activación es válido durante 48 horas.</p>
          <Button as={Link} to="/login" variant="secondary">
            Ir a iniciar sesión
          </Button>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      wide
      title="Registro de aspirante"
      subtitle="Crea tu cuenta para solicitar matrícula en las carreras por encuentro."
      footer={
        <>
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
        </>
      }
    >
      <form className={styles.form} onSubmit={alEnviar} noValidate>
        {errorGeneral && <Alert tone="danger">{errorGeneral}</Alert>}
        <div className={styles.row}>
          <Input label="Nombre" autoComplete="given-name" required {...campo('nombre')} />
          <Input label="Apellidos" autoComplete="family-name" required {...campo('apellidos')} />
        </div>
        <div className={styles.row}>
          <Input
            label="Carnet de identidad"
            inputMode="numeric"
            maxLength={11}
            hint="11 dígitos, sin espacios ni guiones"
            required
            {...campo('ci')}
          />
          <Input label="Celular" type="tel" inputMode="numeric" maxLength={8} hint="Ej: 55123456" required {...campo('celular')} />
        </div>
        <Input
          label="Correo electrónico"
          type="email"
          autoComplete="email"
          hint="Lo usarás para iniciar sesión y recibir notificaciones"
          required
          {...campo('email')}
        />
        <div className={styles.row}>
          <Input label="Contraseña" type="password" autoComplete="new-password" required {...campo('password')} />
          <Input label="Repite la contraseña" type="password" autoComplete="new-password" required {...campo('confirmacion')} />
        </div>
        <Checkbox
          label={
            <>
              Acepto que mis datos sean tratados conforme a la{' '}
              <Link to="/privacidad" target="_blank">
                Política de Privacidad
              </Link>{' '}
              de la UHO para fines de gestión académica.
            </>
          }
          {...checkbox('acepta_privacidad')}
        />
        <Button type="submit" icon={UserPlus} loading={enviando} fullWidth>
          Crear cuenta
        </Button>
      </form>
    </AuthCard>
  )
}
