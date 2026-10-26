import { Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Alert, Button, Checkbox, ConfirmDialog, Input, Modal, Select, Textarea } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useFormulario } from '../../../hooks/useFormulario'
import { useOpciones } from '../../../hooks/useOpciones'
import { useValorDiferido } from '../../../hooks/useValorDiferido'
import { mensajeDeError } from '../../../services/errores'
import { cumFum, facultades } from '../../../services/nomencladores'
import { envios } from '../../../services/notificaciones'
import { usuarios } from '../../../services/usuarios'
import styles from './Envios.module.css'

const INICIALES = { tipo: '', rol: '', entidad: '', asunto: '', cuerpo: '', por_correo: false }
const ID_FORMULARIO = 'nuevo-envio'

/** Grupo en el formato de la API, o null si aún está incompleto. */
function grupoDe(v, esGlobal) {
  if (v.tipo === 'aspirantes') return { tipo: 'aspirantes' }
  if (v.tipo === 'rol') return v.rol ? { tipo: 'rol', rol: v.rol } : null
  if (v.tipo === 'entidad') {
    if (!esGlobal) return { tipo: 'entidad' }
    if (!v.entidad) return null
    const [campo, id] = v.entidad.split(':')
    return { tipo: 'entidad', [campo]: Number(id) }
  }
  return null
}

function validar(v) {
  const errores = {}
  if (!v.tipo) errores.tipo = 'Selecciona a quién va dirigido.'
  if (v.tipo === 'rol' && !v.rol) errores.rol = 'Selecciona el rol.'
  if (!v.asunto.trim()) errores.asunto = 'Escribe el asunto.'
  if (!v.cuerpo.trim()) errores.cuerpo = 'Escribe el mensaje.'
  return errores
}

/** Formulario de envío masivo (RF-076) con recuento de destinatarios y confirmación. */
export function NuevoEnvio({ onClose }) {
  const { esGlobal, usuario } = useAuth()
  const formulario = useFormulario(INICIALES)
  const { valores, campo, checkbox } = formulario
  const [roles, setRoles] = useState([])
  const [conteo, setConteo] = useState(null)
  const [confirmar, setConfirmar] = useState(false)
  const opcionesFacultad = useOpciones(esGlobal ? facultades : null)
  const opcionesCum = useOpciones(esGlobal ? cumFum : null)

  useEffect(() => {
    usuarios.rolesAsignables().then(setRoles, () => setRoles([]))
  }, [])

  // Recuento de destinatarios cada vez que el grupo queda completo.
  const grupo = useValorDiferido(JSON.stringify(grupoDe(valores, esGlobal)), 200)
  useEffect(() => {
    const datos = JSON.parse(grupo)
    if (!datos) return undefined
    let vigente = true
    envios
      .contar(datos)
      .then((r) => vigente && setConteo({ ...r, grupo }))
      .catch((error) => vigente && setConteo({ error: mensajeDeError(error), grupo }))
    return () => {
      vigente = false
    }
  }, [grupo])
  const conteoVigente = conteo?.grupo === grupo ? conteo : null

  const tipos = [
    { value: 'rol', label: 'Usuarios de un rol' },
    { value: 'entidad', label: esGlobal ? 'Usuarios de una entidad' : `Usuarios de ${usuario.entidad?.nombre ?? 'mi entidad'}` },
    ...(esGlobal ? [{ value: 'aspirantes', label: 'Todos los aspirantes' }] : []),
  ]
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]

  function revisar(evento) {
    evento.preventDefault()
    const errores = validar(valores)
    if (esGlobal && valores.tipo === 'entidad' && !valores.entidad) errores.entidad = 'Selecciona la entidad.'
    formulario.setErrores(errores)
    if (Object.keys(errores).length) return
    setConfirmar(true)
  }

  async function enviar() {
    setConfirmar(false)
    const envio = await formulario.enviar((v) =>
      envios.crear({ grupo: grupoDe(v, esGlobal), asunto: v.asunto, cuerpo: v.cuerpo, por_correo: v.por_correo }),
    )
    if (envio) onClose(envio)
  }

  return (
    <>
      <Modal
        open
        onClose={() => onClose()}
        title="Nuevo envío masivo"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => onClose()} disabled={formulario.enviando}>
              Cancelar
            </Button>
            <Button type="submit" form={ID_FORMULARIO} icon={Send} loading={formulario.enviando}>
              Enviar
            </Button>
          </>
        }
      >
        <form id={ID_FORMULARIO} className={styles.form} onSubmit={revisar} noValidate>
          {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
          <div className={styles.fila}>
            <Select label="Destinatarios" options={tipos} placeholder="Selecciona…" {...campo('tipo')} />
            {valores.tipo === 'rol' && (
              <Select label="Rol" options={roles.map((r) => ({ value: r.codigo, label: r.nombre }))} placeholder="Selecciona…" {...campo('rol')} />
            )}
            {valores.tipo === 'entidad' && esGlobal && (
              <Select label="Entidad" options={entidades} placeholder="Selecciona…" {...campo('entidad')} />
            )}
          </div>
          {conteoVigente &&
            (conteoVigente.error ? (
              <Alert tone="warning">{conteoVigente.error}</Alert>
            ) : (
              <Alert tone={conteoVigente.destinatarios ? 'info' : 'warning'}>
                {conteoVigente.descripcion}: {conteoVigente.destinatarios} destinatario(s).
              </Alert>
            ))}
          <Input label="Asunto" maxLength={200} {...campo('asunto')} />
          <Textarea label="Mensaje" rows={8} hint="Puedes usar {{ nombre }} para incluir el nombre de cada destinatario." {...campo('cuerpo')} />
          <Checkbox label="Enviar también por correo electrónico" {...checkbox('por_correo')} />
        </form>
      </Modal>
      <ConfirmDialog
        open={confirmar}
        title="Confirmar envío"
        message={`Se notificará a ${conteoVigente?.destinatarios ?? 'los'} destinatario(s)${valores.por_correo ? ', también por correo' : ''}. Esta acción no se puede deshacer.`}
        confirmLabel="Enviar"
        tone="primary"
        onConfirm={enviar}
        onCancel={() => setConfirmar(false)}
      />
    </>
  )
}
