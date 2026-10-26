import { KeyRound, Save } from 'lucide-react'
import { useState } from 'react'
import { Alert, Avatar, Button, Card, CardBody, CardHeader, Input, PageHeader, useToast } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { useFormulario } from '../../hooks/useFormulario'
import { actualizarPerfil, cambiarPassword } from '../../services/perfil'
import { MENSAJE_CELULAR, PATRON_CELULAR, validarPassword } from '../../utils/validaciones'
import styles from './MiPerfil.module.css'

const MAX_FOTO_MB = 5

/** Perfil propio (RF-018): datos de contacto, foto y contraseña. Común a internos y aspirantes. */
export function MiPerfil() {
  const { usuario, actualizarUsuario } = useAuth()
  const toast = useToast()
  const nombre = `${usuario.nombre} ${usuario.apellidos}`.trim() || usuario.username

  const datos = useFormulario({ celular: usuario.celular ?? '' })
  const [foto, setFoto] = useState(null)
  const [errorFoto, setErrorFoto] = useState('')
  // Cambiar la key vacía el <input type="file"> tras guardar.
  const [versionFoto, setVersionFoto] = useState(0)
  const clave = useFormulario({ actual: '', password: '', confirmacion: '' })

  function elegirFoto(evento) {
    const archivo = evento.target.files?.[0] ?? null
    setErrorFoto(archivo && archivo.size > MAX_FOTO_MB * 1024 * 1024 ? `La imagen no puede superar ${MAX_FOTO_MB} MB.` : '')
    setFoto(archivo)
  }

  async function guardarDatos(evento) {
    evento.preventDefault()
    if (errorFoto) return
    const perfil = await datos.enviar(
      ({ celular }) => actualizarPerfil({ celular, foto }),
      ({ celular }) => (celular && !PATRON_CELULAR.test(celular) ? { celular: MENSAJE_CELULAR } : {}),
    )
    if (perfil) {
      actualizarUsuario(perfil)
      setFoto(null)
      setVersionFoto((v) => v + 1)
      toast.exito('Tus datos se guardaron.')
    }
  }

  async function guardarClave(evento) {
    evento.preventDefault()
    const ok = await clave.enviar(
      async ({ actual, password }) => {
        await cambiarPassword(actual, password)
        return true
      },
      ({ password, confirmacion }) => validarPassword(password, confirmacion),
    )
    if (ok) {
      clave.setValores({ actual: '', password: '', confirmacion: '' })
      toast.exito('Tu contraseña se cambió.')
    }
  }

  return (
    <>
      <PageHeader title="Mi perfil" />
      <div className={styles.grid}>
        <Card>
          <CardHeader title="Datos personales" />
          <CardBody>
            <div className={styles.identidad}>
              <Avatar nombre={nombre} foto={usuario.foto} size="lg" />
              <div>
                <strong className={styles.nombre}>{nombre}</strong>
                <dl className={styles.datos}>
                  {usuario.email && (
                    <>
                      <dt>Correo</dt>
                      <dd>{usuario.email}</dd>
                    </>
                  )}
                  {usuario.ci && (
                    <>
                      <dt>CI</dt>
                      <dd>{usuario.ci}</dd>
                    </>
                  )}
                  <dt>Rol</dt>
                  <dd>{usuario.rol?.nombre ?? 'Superadmin'}</dd>
                </dl>
              </div>
            </div>
            <form className={styles.form} onSubmit={guardarDatos} noValidate>
              {datos.errorGeneral && <Alert tone="danger">{datos.errorGeneral}</Alert>}
              <Input label="Celular" type="tel" inputMode="numeric" maxLength={8} {...datos.campo('celular')} />
              <Input
                key={versionFoto}
                label="Foto de perfil"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hint="JPG, PNG o WEBP, máximo 5 MB"
                error={errorFoto || datos.errores.foto}
                onChange={elegirFoto}
              />
              <Button type="submit" icon={Save} loading={datos.enviando}>
                Guardar cambios
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Contraseña" />
          <CardBody>
            {usuario.origen === 'sgu' ? (
              <Alert tone="info">Tu contraseña se gestiona en el Sistema de Gestión de Usuarios de la UHO.</Alert>
            ) : (
              <form className={styles.form} onSubmit={guardarClave} noValidate>
                {clave.errorGeneral && <Alert tone="danger">{clave.errorGeneral}</Alert>}
                <Input label="Contraseña actual" type="password" autoComplete="current-password" {...clave.campo('actual')} />
                <Input
                  label="Nueva contraseña"
                  type="password"
                  autoComplete="new-password"
                  {...clave.campo('password')}
                  error={clave.errores.password || clave.errores.nueva}
                />
                <Input label="Repite la nueva contraseña" type="password" autoComplete="new-password" {...clave.campo('confirmacion')} />
                <Button type="submit" variant="secondary" icon={KeyRound} loading={clave.enviando}>
                  Cambiar contraseña
                </Button>
              </form>
            )}
          </CardBody>
        </Card>
      </div>
    </>
  )
}
