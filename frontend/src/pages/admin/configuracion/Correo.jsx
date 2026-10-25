import { Send } from 'lucide-react'
import { useState } from 'react'
import { useCarga } from '../../../hooks/useCarga'
import { Alert, Button, Checkbox, Input, useToast } from '../../../components/ui'
import { smtp } from '../../../services/configuracion'
import { mensajeDeError } from '../../../services/errores'
import styles from './Configuracion.module.css'
import { SeccionFormulario } from './SeccionFormulario'

function validar(v) {
  const errores = {}
  if (v.activo && !v.host.trim()) errores.host = 'Indica el servidor SMTP.'
  if (v.activo && !v.remitente.trim()) errores.remitente = 'Indica el remitente por defecto.'
  if (v.usar_tls && v.usar_ssl) errores.usar_ssl = 'Elige STARTTLS o SSL/TLS, no ambos.'
  return errores
}

function datos(v) {
  const { activo, host, puerto, usuario, usar_tls, usar_ssl, remitente, password } = v
  return { activo, host, puerto, usuario, usar_tls, usar_ssl, remitente, ...(password ? { password } : {}) }
}

function Prueba({ editable }) {
  const [destinatario, setDestinatario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const toast = useToast()

  async function probar() {
    setEnviando(true)
    try {
      toast.exito((await smtp.probar(destinatario)).mensaje)
    } catch (error) {
      toast.error(mensajeDeError(error))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className={styles.color}>
      <Input
        label="Enviar un correo de prueba a"
        type="email"
        value={destinatario}
        onChange={(e) => setDestinatario(e.target.value)}
        disabled={!editable}
      />
      <Button variant="secondary" icon={Send} loading={enviando} disabled={!editable || !destinatario} onClick={probar}>
        Probar
      </Button>
    </div>
  )
}

/** Servidor de correo (RF-009, RE-010). */
export function Correo({ editable }) {
  const carga = useCarga(smtp.obtener)
  const toast = useToast()
  // La contraseña nunca llega de la API: el campo empieza vacío.
  const cargaFormulario = { ...carga, datos: carga.datos && { ...carga.datos, password: '' } }

  return (
    <div className={styles.pila}>
      <SeccionFormulario
        titulo="Servidor de correo (SMTP)"
        descripcion="Mientras esta configuración esté desactivada, el sistema usa la del archivo .env del servidor."
        carga={cargaFormulario}
        editable={editable}
        validar={validar}
        guardar={(v) => smtp.guardar(datos(v)).then((guardado) => ({ ...guardado, password: '' }))}
        onGuardado={() => toast.exito('La configuración de correo se guardó. Usa "Probar" para comprobarla.')}
      >
        {({ campo, checkbox, valores }) => (
          <>
            <Checkbox label="Usar esta configuración en lugar de la del servidor" className={styles.completo} {...checkbox('activo')} />
            <Input label="Servidor" placeholder="smtp.uho.edu.cu" {...campo('host')} />
            <Input label="Puerto" type="number" min={1} max={65535} {...campo('puerto')} />
            <Input label="Usuario" autoComplete="off" {...campo('usuario')} />
            <Input
              label="Contraseña"
              type="password"
              autoComplete="new-password"
              hint={valores.password_configurada ? 'Hay una contraseña guardada. Déjala vacía para conservarla.' : 'Sin contraseña guardada.'}
              {...campo('password')}
            />
            <Input label="Remitente por defecto" placeholder="SIGECUE <no-responder@uho.edu.cu>" className={styles.completo} {...campo('remitente')} />
            <Checkbox label="Usar STARTTLS (puerto 587)" {...checkbox('usar_tls')} />
            <Checkbox label="Usar SSL/TLS implícito (puerto 465)" {...checkbox('usar_ssl')} />
          </>
        )}
      </SeccionFormulario>
      <Alert tone="info" title="Probar el envío">
        La prueba usa la configuración guardada. Guarda los cambios antes de probar.
      </Alert>
      <Prueba editable={editable} />
    </div>
  )
}
