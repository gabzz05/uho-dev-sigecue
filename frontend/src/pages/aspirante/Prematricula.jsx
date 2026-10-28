import { Eye, Save, Send, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { Alert, Button, Card, CardBody, CardHeader, ConfirmDialog, EmptyState, Input, PageHeader, Spinner, StatusBadge, useToast } from '../../components/ui'
import { useCarga } from '../../hooks/useCarga'
import { obtenerArchivo } from '../../services/aspirante'
import { mensajeDeError } from '../../services/errores'
import { miPrematricula } from '../../services/prematricula'
import { FORMATOS_DOCUMENTO, formatearTamano } from '../../utils/archivos'
import { ESTADOS_PREMATRICULA, REVISION_ELEMENTO } from '../../utils/estadosPrematricula'
import { formatearFecha } from '../../utils/fechas'
import styles from './Aspirante.module.css'

const cargar = () => miPrematricula.listar().then((lista) => (lista.length ? miPrematricula.obtener(lista[0].id) : null))

/** Prematrícula del aspirante otorgado (RF-065, RF-067): se completa en varias sesiones y se envía. */
export function Prematricula() {
  const carga = useCarga(cargar)
  const [actualizada, setActualizada] = useState(null)
  const prematricula = actualizada ?? carga.datos

  if (carga.cargando) return <Spinner label="Cargando tu prematrícula" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>
  if (!prematricula) {
    return (
      <>
        <PageHeader title="Prematrícula" />
        <EmptyState title="Todavía no tienes prematrícula" message="Se abre cuando obtienes plaza y la universidad fija el período." />
      </>
    )
  }
  return <Formulario prematricula={prematricula} onCambio={setActualizada} />
}

function Formulario({ prematricula, onCambio }) {
  const toast = useToast()
  const [confirmando, setConfirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const { periodo } = prematricula
  const puedeEnviar = ['pendiente', 'borrador', 'con_correcciones'].includes(prematricula.estado) && (periodo.abierto || (periodo.cerrado && prematricula.estado === 'con_correcciones'))

  async function enviar() {
    setEnviando(true)
    try {
      onCambio(await miPrematricula.enviar(prematricula.id))
      toast.exito('Enviaste tu prematrícula. La entidad la revisará.')
      setConfirmando(false)
    } catch (e) {
      toast.error(mensajeDeError(e))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Prematrícula"
        subtitle={`${prematricula.carrera} — ${prematricula.entidad}. Plazo: del ${formatearFecha(periodo.fecha_inicio)} al ${formatearFecha(periodo.fecha_cierre)}.`}
      />
      <div className={styles.pila}>
        <div className={styles.resumenSolicitud}>
          <StatusBadge estado={prematricula.estado} mapa={ESTADOS_PREMATRICULA} />
        </div>
        <Aviso prematricula={prematricula} />

        <Card>
          <CardHeader title="Documentos y datos" />
          <CardBody>
            <p className={styles.ayuda}>
              El carnet de identidad y la certificación se toman de tu perfil: solo tendrás que subirlos de nuevo si la entidad los rechaza. Los
              archivos son PDF, JPG o PNG de hasta 5 MB. Usas {formatearTamano(prematricula.limites.cuota_usada)} de{' '}
              {formatearTamano(prematricula.limites.cuota_maxima)}.
            </p>
            <ul className={styles.documentos}>
              {prematricula.elementos.map((e) => (
                <Elemento key={e.id} prematricula={prematricula} elemento={e} onCambio={onCambio} />
              ))}
            </ul>
          </CardBody>
        </Card>

        {puedeEnviar && (
          <div className={styles.barraAcciones}>
            {prematricula.faltantes.length > 0 && <span className={styles.ayuda}>Falta: {prematricula.faltantes.join(', ')}.</span>}
            <Button icon={Send} onClick={() => setConfirmando(true)} disabled={prematricula.faltantes.length > 0}>
              {prematricula.estado === 'con_correcciones' ? 'Reenviar prematrícula' : 'Enviar prematrícula'}
            </Button>
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirmando}
        title="Enviar prematrícula"
        message="La entidad revisará cada documento. Mientras la revisa no podrás modificarla."
        confirmLabel="Enviar"
        tone="primary"
        loading={enviando}
        onConfirm={enviar}
        onCancel={() => setConfirmando(false)}
      />
    </>
  )
}

function Aviso({ prematricula }) {
  const { estado, periodo } = prematricula
  if (estado === 'aprobada') return <Alert tone="success" title="Prematrícula aprobada">La entidad te informará los próximos pasos.</Alert>
  if (estado === 'completada') return <Alert tone="info">Enviaste tu prematrícula. La entidad la está revisando.</Alert>
  if (estado === 'con_correcciones') {
    return (
      <Alert tone="warning" title="Hay correcciones">
        Corrige lo rechazado y vuelve a enviarla. No pierdes tu plaza.
      </Alert>
    )
  }
  if (estado === 'incompleta') return <Alert tone="warning">El plazo cerró sin que enviaras la prematrícula. Comunícate con tu entidad: no pierdes la plaza.</Alert>
  if (!periodo.abierto && !periodo.cerrado) return <Alert tone="info">La prematrícula abre el {formatearFecha(periodo.fecha_inicio)}.</Alert>
  return <Alert tone="info">Puedes guardarla y terminarla en varias sesiones hasta el {formatearFecha(periodo.fecha_cierre)}.</Alert>
}

function Elemento({ prematricula, elemento, onCambio }) {
  const toast = useToast()
  const entrada = useRef(null)
  const [texto, setTexto] = useState(elemento.valor_texto)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')

  async function ejecutar(accion, mensaje) {
    setOcupado(true)
    setError('')
    try {
      onCambio(await accion())
      toast.exito(mensaje)
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  function subir(evento) {
    const archivo = evento.target.files?.[0]
    evento.target.value = ''
    if (!archivo) return
    if (archivo.size > 5 * 1024 * 1024) {
      setError('El archivo no puede superar 5 MB.')
      return
    }
    ejecutar(() => miPrematricula.subirArchivo(prematricula.id, elemento.id, archivo), `${elemento.nombre}: se guardó el archivo.`)
  }

  async function ver() {
    const pestana = window.open('', '_blank')
    try {
      const url = URL.createObjectURL(await obtenerArchivo(elemento.archivo.archivo))
      if (pestana) pestana.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (e) {
      pestana?.close()
      toast.error(mensajeDeError(e))
    }
  }

  const deCampo = elemento.tipo !== 'documento_perfil'
  return (
    <li className={styles.documento}>
      <div className={styles.documentoInfo}>
        <strong>{elemento.nombre}</strong>
        {elemento.entregado && <StatusBadge estado={elemento.revision} mapa={REVISION_ELEMENTO} />}
        <span className={styles.documentoEstado}>
          {elemento.tipo === 'texto'
            ? null
            : elemento.archivo
              ? `${elemento.archivo.nombre_original} · ${formatearTamano(elemento.archivo.tamano)}${deCampo ? '' : ' · de tu perfil'}`
              : elemento.requerido
                ? 'Sin entregar'
                : 'Sin entregar (opcional)'}
        </span>
        {elemento.revision === 'rechazado' && <span className={styles.error}>Corrige: {elemento.observacion}</span>}
        {error && (
          <span className={styles.error} role="alert">
            {error}
          </span>
        )}
        {elemento.tipo === 'texto' && (
          <div className={styles.formularioEnLinea}>
            <Input label={elemento.nombre} value={texto} disabled={!elemento.editable} onChange={(e) => setTexto(e.target.value)} />
            {elemento.editable && (
              <Button size="sm" variant="secondary" icon={Save} loading={ocupado} onClick={() => ejecutar(() => miPrematricula.guardarTexto(prematricula.id, elemento.id, texto), 'Se guardó.')}>
                Guardar
              </Button>
            )}
          </div>
        )}
      </div>
      <div className={styles.documentoAcciones}>
        {elemento.archivo && (
          <Button variant="ghost" size="sm" icon={Eye} onClick={ver} aria-label={`Ver ${elemento.nombre}`}>
            Ver
          </Button>
        )}
        {elemento.editable && deCampo && elemento.tipo !== 'texto' && (
          <>
            <input
              ref={entrada}
              type="file"
              accept={elemento.tipo === 'imagen' ? 'image/jpeg,image/png' : FORMATOS_DOCUMENTO}
              className={styles.srOnly}
              tabIndex={-1}
              aria-hidden="true"
              onChange={subir}
            />
            <Button
              size="sm"
              variant={elemento.archivo ? 'secondary' : 'primary'}
              icon={Upload}
              loading={ocupado}
              onClick={() => entrada.current?.click()}
              aria-label={`${elemento.archivo ? 'Sustituir' : 'Subir'} ${elemento.nombre}`}
            >
              {elemento.archivo ? 'Sustituir' : 'Subir'}
            </Button>
          </>
        )}
        {elemento.editable && !deCampo && (
          <Button as={Link} to="/aspirante/completar-perfil" size="sm" variant="secondary">
            Sustituir en mi perfil
          </Button>
        )}
      </div>
    </li>
  )
}
