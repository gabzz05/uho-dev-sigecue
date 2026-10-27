import { ArrowLeft, CheckCircle2, Eye, MessageSquarePlus, Pencil, RotateCcw } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import {
  Alert,
  Avatar,
  Badge,
  BotonConfirmado,
  Button,
  Card,
  CardBody,
  CardHeader,
  Checkbox,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  StatusBadge,
  Textarea,
  useToast,
} from '../../../components/ui'
import { useArchivoPrivado } from '../../../hooks/useArchivoPrivado'
import { useCarga } from '../../../hooks/useCarga'
import { useFormulario } from '../../../hooks/useFormulario'
import { mensajeDeError } from '../../../services/errores'
import { observaciones as apiObservaciones, solicitudesAdmin } from '../../../services/solicitudes'
import { formatearTamano } from '../../../utils/archivos'
import { ESTADOS_OBSERVACION, ESTADOS_SOLICITUD } from '../../../utils/estadosSolicitud'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Solicitudes.module.css'
import { VisorDocumento } from './VisorDocumento'

const OBJETIVOS = [
  { value: 'documento', label: 'Un documento' },
  { value: 'indice', label: 'Índice académico' },
  { value: 'centro_trabajo', label: 'Centro de trabajo' },
  { value: 'foto', label: 'Foto' },
]

/** Detalle de una solicitud (RF-054) y su revisión: índice, observaciones e historial (RF-055). */
export function DetalleSolicitud() {
  const { id } = useParams()
  const cargar = useCallback(() => solicitudesAdmin.obtener(id), [id])
  const carga = useCarga(cargar)
  const [actualizada, setActualizada] = useState(null)
  const solicitud = actualizada ?? carga.datos
  const recargar = useCallback(() => solicitudesAdmin.obtener(id).then(setActualizada), [id])

  if (carga.cargando) return <Spinner label="Cargando la solicitud" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const { aspirante, permisos, elegibilidad } = solicitud
  const nombre = `${aspirante.nombre} ${aspirante.apellidos}`

  return (
    <>
      <PageHeader
        title={nombre}
        subtitle={`Solicitud de la convocatoria ${solicitud.convocatoria}`}
        actions={
          <Button as={Link} to="/admin/solicitudes" variant="ghost" icon={ArrowLeft}>
            Volver
          </Button>
        }
      />
      <div className={styles.pila}>
        <div className={styles.resumen}>
          <StatusBadge estado={solicitud.estado} mapa={ESTADOS_SOLICITUD} />
          {solicitud.revision_documental_pendiente && <Badge tone="warning">Revisión documental pendiente</Badge>}
          {elegibilidad.elegible ? (
            <Badge tone="success">Elegible para el otorgamiento</Badge>
          ) : (
            <span className={styles.apagado}>Fuera del ranking: {elegibilidad.motivos.join(' · ')}</span>
          )}
        </div>

        <div className={styles.dosColumnas}>
          <DatosAspirante aspirante={aspirante} />
          <Indice solicitud={solicitud} onCambio={setActualizada} />
        </div>

        <Card>
          <CardHeader title={`Carreras (${solicitud.carreras.length})`} />
          <CardBody>
            <ul className={styles.listaCompacta}>
              {solicitud.carreras.map((c) => (
                <li key={c.oferta.id}>
                  <strong>{c.prioridad}.</strong> {c.oferta.carrera_nombre} <span className={styles.apagado}>— {c.oferta.entidad_nombre}</span>
                </li>
              ))}
            </ul>
            <p className={styles.apagado}>Confirmada el {formatearFechaHora(solicitud.confirmada_at)}.</p>
          </CardBody>
        </Card>

        <Documentos solicitud={solicitud} />
        <Observaciones solicitud={solicitud} onCambio={setActualizada} recargar={recargar} puedeObservar={permisos.revisar} />
        <Historial eventos={solicitud.historial} />
      </div>
    </>
  )
}

function DatosAspirante({ aspirante }) {
  const foto = useArchivoPrivado(aspirante.foto)
  const nombre = `${aspirante.nombre} ${aspirante.apellidos}`
  return (
    <Card>
      <CardHeader title="Datos del aspirante" />
      <CardBody>
        <div className={styles.identidad}>
          <Avatar nombre={nombre} foto={foto} size="lg" />
          <dl className={styles.datos}>
            <dt>CI</dt>
            <dd>{aspirante.ci}</dd>
            <dt>Correo</dt>
            <dd>{aspirante.email}</dd>
            <dt>Celular</dt>
            <dd>{aspirante.celular}</dd>
            <dt>Centro de trabajo</dt>
            <dd>{aspirante.centro_trabajo || '—'}</dd>
            <dt>Perfil</dt>
            <dd>{aspirante.perfil_completo ? 'Completo' : 'Incompleto'}</dd>
          </dl>
        </div>
      </CardBody>
    </Card>
  )
}

function Indice({ solicitud, onCambio }) {
  const toast = useToast()
  const { aspirante, permisos } = solicitud
  const formulario = useFormulario({ indice: aspirante.indice_validado ?? aspirante.indice_declarado ?? '' })

  async function validar(evento) {
    evento.preventDefault()
    const datos = await formulario.enviar(
      ({ indice }) => solicitudesAdmin.validarIndice(solicitud.id, Number(indice)),
      ({ indice }) => (indice === '' || Number(indice) < 0 || Number(indice) > 100 ? { indice: 'Escribe un número entre 0 y 100.' } : {}),
    )
    if (datos) {
      onCambio(datos)
      toast.exito('El índice quedó validado.')
    }
  }

  return (
    <Card>
      <CardHeader title="Índice académico" />
      <CardBody>
        <dl className={styles.datos}>
          <dt>Declarado</dt>
          <dd>{aspirante.indice_declarado ?? '—'}</dd>
          <dt>Validado</dt>
          <dd>
            {aspirante.indice_validado != null
              ? `${aspirante.indice_validado} · ${aspirante.indice_validado_por ?? ''} · ${formatearFechaHora(aspirante.indice_validado_at)}`
              : 'Sin validar'}
          </dd>
        </dl>
        {permisos.validar_indice ? (
          <form className={styles.formularioEnLinea} onSubmit={validar} noValidate>
            {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
            <Input
              label="Índice según la certificación"
              type="number"
              min={0}
              max={100}
              step={0.01}
              hint="Una sola entidad lo valida; después solo la Comisión de Ingreso puede cambiarlo."
              {...formulario.campo('indice')}
            />
            <Button type="submit" icon={CheckCircle2} loading={formulario.enviando}>
              {aspirante.indice_validado != null ? 'Corregir validación' : 'Validar índice'}
            </Button>
          </form>
        ) : (
          aspirante.indice_validado == null &&
          permisos.revisar && <p className={styles.apagado}>El índice tiene una observación pendiente o ya no se puede validar.</p>
        )}
      </CardBody>
    </Card>
  )
}

function Documentos({ solicitud }) {
  const [abierto, setAbierto] = useState(null)
  return (
    <Card>
      <CardHeader title="Documentos" />
      <CardBody>
        {!solicitud.permisos.descargar_documentos && (
          <Alert tone="info">Tu rol no tiene permiso para abrir los documentos personales del aspirante.</Alert>
        )}
        <ul className={styles.documentos}>
          {solicitud.documentos.map(({ tipo, documento }) => (
            <li key={tipo.id}>
              <div>
                <strong>{tipo.nombre}</strong>
                <span className={styles.apagado}>
                  {documento
                    ? `${documento.nombre_original} · ${formatearTamano(documento.tamano)} · v${documento.version} · ${formatearFechaHora(documento.subido_at)}`
                    : 'Sin subir'}
                </span>
              </div>
              {documento?.archivo && (
                <Button variant="ghost" size="sm" icon={Eye} onClick={() => setAbierto({ documento, titulo: tipo.nombre })} aria-label={`Ver ${tipo.nombre}`}>
                  Ver
                </Button>
              )}
            </li>
          ))}
        </ul>
      </CardBody>
      <VisorDocumento documento={abierto?.documento} titulo={abierto?.titulo} onClose={() => setAbierto(null)} />
    </Card>
  )
}

function Observaciones({ solicitud, onCambio, recargar, puedeObservar }) {
  const toast = useToast()
  const [nueva, setNueva] = useState(false)
  const [editando, setEditando] = useState(null)
  const [reabriendo, setReabriendo] = useState(null)

  async function resolver(observacion) {
    try {
      await apiObservaciones.resolver(observacion.id)
      await recargar()
      toast.exito('La observación quedó resuelta.')
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  return (
    <Card>
      <CardHeader
        title="Observaciones"
        actions={
          puedeObservar && (
            <Button size="sm" icon={MessageSquarePlus} onClick={() => setNueva(true)}>
              Nueva observación
            </Button>
          )
        }
      />
      <CardBody>
        {solicitud.observaciones.length === 0 ? (
          <p className={styles.apagado}>Sin observaciones.</p>
        ) : (
          <ul className={styles.observaciones}>
            {solicitud.observaciones.map((o) => (
              <li key={o.id}>
                <div className={styles.observacionCabecera}>
                  <strong>{o.elemento}</strong>
                  <StatusBadge estado={o.estado} mapa={ESTADOS_OBSERVACION} />
                  {o.afecta_elegibilidad && <Badge tone="warning">Afecta la elegibilidad</Badge>}
                </div>
                <p className={styles.textoObservacion}>{o.texto}</p>
                <span className={styles.apagado}>
                  {o.entidad_nombre} · {o.autor_nombre ?? '—'} · {formatearFechaHora(o.created_at)}
                  {o.corregida_at && ` · corregida ${formatearFechaHora(o.corregida_at)}`}
                </span>
                {o.puede_gestionar && o.estado !== 'resuelta' && (
                  <div className={styles.accionesObservacion}>
                    <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditando(o)} aria-label={`Editar la observación sobre ${o.elemento}`}>
                      Editar
                    </Button>
                    {o.estado === 'corregida' && (
                      <Button variant="ghost" size="sm" icon={RotateCcw} onClick={() => setReabriendo(o)} aria-label={`Reabrir la observación sobre ${o.elemento}`}>
                        Reabrir
                      </Button>
                    )}
                    <BotonConfirmado
                      variant="secondary"
                      size="sm"
                      icon={CheckCircle2}
                      aria-label={`Resolver la observación sobre ${o.elemento}`}
                      titulo="Resolver observación"
                      tone="primary"
                      mensaje="La observación dejará de bloquear la solicitud en el ranking."
                      onConfirm={() => resolver(o)}
                    >
                      Resolver
                    </BotonConfirmado>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
      {nueva && <NuevaObservacion solicitud={solicitud} onClose={() => setNueva(false)} onCreada={onCambio} />}
      {editando && <EditarObservacion observacion={editando} onClose={() => setEditando(null)} onGuardada={recargar} />}
      {reabriendo && <ReabrirObservacion observacion={reabriendo} onClose={() => setReabriendo(null)} onReabierta={recargar} />}
    </Card>
  )
}

/** Por defecto: sí para el índice y los documentos marcados (certificación); no para el resto. */
function afectaPorDefecto(objetivo, tipo) {
  if (objetivo === 'indice') return true
  return objetivo === 'documento' && Boolean(tipo?.afecta_elegibilidad)
}

function NuevaObservacion({ solicitud, onClose, onCreada }) {
  const toast = useToast()
  const tipos = solicitud.documentos.map((d) => d.tipo)
  const formulario = useFormulario({ objetivo: 'documento', tipo_documento: String(tipos[0]?.id ?? ''), texto: '', afecta: null })
  const { objetivo, tipo_documento: tipoId, afecta } = formulario.valores
  const tipo = tipos.find((t) => String(t.id) === tipoId)
  const afectaActual = afecta ?? afectaPorDefecto(objetivo, tipo)

  async function guardar() {
    const datos = await formulario.enviar(
      ({ texto }) =>
        solicitudesAdmin.observar(solicitud.id, {
          objetivo,
          tipo_documento: objetivo === 'documento' ? Number(tipoId) : null,
          texto: texto.trim(),
          afecta_elegibilidad: afectaActual,
        }),
      ({ texto }) => (texto.trim() ? {} : { texto: 'Explica qué hay que corregir.' }),
    )
    if (datos) {
      onCreada(datos)
      toast.exito('Se registró la observación y se avisó al aspirante.')
      onClose()
    }
  }

  const cambiarObjetivo = (e) => formulario.setValores((v) => ({ ...v, objetivo: e.target.value, afecta: null }))
  const cambiarTipo = (e) => formulario.setValores((v) => ({ ...v, tipo_documento: e.target.value, afecta: null }))

  return (
    <Modal
      open
      onClose={onClose}
      title="Nueva observación"
      description="El aspirante podrá corregir solo el elemento observado, aunque la convocatoria esté cerrada."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={guardar} loading={formulario.enviando}>
            Observar
          </Button>
        </>
      }
    >
      <div className={styles.formulario}>
        {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
        <Select label="Qué observas" options={OBJETIVOS} value={objetivo} onChange={cambiarObjetivo} />
        {objetivo === 'documento' && (
          <Select label="Documento" options={tipos.map((t) => ({ value: String(t.id), label: t.nombre }))} value={tipoId} onChange={cambiarTipo} />
        )}
        <Textarea label="Observación" required rows={4} maxLength={2000} {...formulario.campo('texto')} />
        <Checkbox
          label="Afecta la elegibilidad: anula el índice validado y exige validarlo de nuevo"
          checked={afectaActual}
          onChange={(e) => formulario.setValores((v) => ({ ...v, afecta: e.target.checked }))}
        />
      </div>
    </Modal>
  )
}

function EditarObservacion({ observacion, onClose, onGuardada }) {
  const toast = useToast()
  const formulario = useFormulario({ texto: observacion.texto, afecta: observacion.afecta_elegibilidad })

  async function guardar() {
    const ok = await formulario.enviar(
      async ({ texto, afecta }) => {
        await apiObservaciones.editar(observacion.id, { texto: texto.trim(), afecta_elegibilidad: afecta })
        await onGuardada()
        return true
      },
      ({ texto }) => (texto.trim() ? {} : { texto: 'La observación no puede quedar vacía.' }),
    )
    if (ok) {
      toast.exito('Se guardó la observación.')
      onClose()
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Editar observación: ${observacion.elemento}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={guardar} loading={formulario.enviando}>
            Guardar
          </Button>
        </>
      }
    >
      <div className={styles.formulario}>
        {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
        <Textarea label="Observación" required rows={4} maxLength={2000} {...formulario.campo('texto')} />
        <Checkbox label="Afecta la elegibilidad" {...formulario.checkbox('afecta')} />
      </div>
    </Modal>
  )
}

function ReabrirObservacion({ observacion, onClose, onReabierta }) {
  const toast = useToast()
  const formulario = useFormulario({ motivo: '' })

  async function reabrir() {
    const ok = await formulario.enviar(
      async ({ motivo }) => {
        await apiObservaciones.reabrir(observacion.id, motivo.trim())
        await onReabierta()
        return true
      },
      ({ motivo }) => (motivo.trim() ? {} : { motivo: 'Explica por qué no vale la corrección.' }),
    )
    if (ok) {
      toast.exito('Se reabrió la observación y se avisó al aspirante.')
      onClose()
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Reabrir observación: ${observacion.elemento}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={reabrir} loading={formulario.enviando}>
            Reabrir
          </Button>
        </>
      }
    >
      <div className={styles.formulario}>
        {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
        <Textarea label="Motivo" required rows={3} maxLength={2000} hint="Se le envía al aspirante." {...formulario.campo('motivo')} />
      </div>
    </Modal>
  )
}

function resumenSeleccion(lista) {
  return lista?.length ? lista.map((o) => `${o.prioridad}. ${o.carrera} (${o.entidad})`).join(', ') : 'ninguna'
}

function Historial({ eventos }) {
  return (
    <Card>
      <CardHeader title="Historial de cambios" />
      <CardBody>
        {eventos.length === 0 ? (
          <p className={styles.apagado}>Sin cambios registrados.</p>
        ) : (
          <ol className={styles.historial}>
            {eventos.map((e) => (
              <li key={e.id}>
                <span className={styles.apagado}>
                  {formatearFechaHora(e.created_at)} · {e.usuario ?? 'Sistema'}
                </span>
                <strong>{e.descripcion}</strong>
                {e.tipo === 'seleccion' && (
                  <span className={styles.apagado}>
                    Antes: {resumenSeleccion(e.antes)}. Después: {resumenSeleccion(e.despues)}.
                  </span>
                )}
                {e.tipo === 'documento' && e.antes && (
                  <span className={styles.apagado}>
                    v{e.antes.version} ({e.antes.archivo}) → v{e.despues.version} ({e.despues.archivo})
                  </span>
                )}
                {e.tipo === 'observacion_reabierta' && e.despues?.motivo && <span className={styles.apagado}>Motivo: {e.despues.motivo}</span>}
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  )
}
