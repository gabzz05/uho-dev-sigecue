import { FilePlus2, Plus, Save, Send, X } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfirmDialog,
  EmptyState,
  Input,
  ListaOrdenable,
  Modal,
  PageHeader,
  Select,
  Spinner,
  StatusBadge,
  useToast,
} from '../../components/ui'
import { useCarga } from '../../hooks/useCarga'
import { perfilAspirante, solicitudes } from '../../services/aspirante'
import { mensajeDeError } from '../../services/errores'
import { formatearFecha, formatearFechaHora } from '../../utils/fechas'
import styles from './Aspirante.module.css'
import { ESTADOS_SOLICITUD, solicitudVigente } from './estados'

const ORDINALES = ['Primera', 'Segunda', 'Tercera', 'Cuarta', 'Quinta', 'Sexta', 'Séptima', 'Octava', 'Novena', 'Décima']
const TIPOS = { facultad: 'Facultad', cum_fum: 'CUM/FUM' }

const cargar = () => Promise.all([perfilAspirante.obtener(), solicitudes.listar(), solicitudes.ofertas()])

/** Por qué no se puede agregar una oferta a la selección (RF-047 a RF-049), o null si se puede. */
function motivoNoDisponible(oferta, seleccion, maximo) {
  if (seleccion.some((o) => o.id === oferta.id)) return 'Ya está en tu selección'
  const mismoTipo = seleccion.find((o) => o.carrera === oferta.carrera && o.tipo_entidad === oferta.tipo_entidad)
  if (mismoTipo) return `Ya la elegiste en ${mismoTipo.entidad_nombre}`
  if (seleccion.length >= maximo) return `Ya tienes ${maximo} carreras`
  return null
}

/** Mis solicitudes: selección de carreras por prioridad y confirmación (pasos 13 a 17 de 7.2). */
export function MiSolicitud() {
  const carga = useCarga(cargar)
  const [solicitudGuardada, setSolicitudGuardada] = useState(null)

  if (carga.cargando) return <Spinner label="Cargando tu solicitud" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const [perfil, lista, ofertas] = carga.datos
  const solicitud = solicitudGuardada ?? solicitudVigente(lista, ofertas.length > 0)

  return (
    <>
      <PageHeader title="Mi solicitud" subtitle="Elige hasta el máximo de carreras permitido y ordénalas por prioridad: la 1 es tu opción principal." />
      <Contenido perfil={perfil} solicitud={solicitud} ofertas={ofertas} onCambio={setSolicitudGuardada} />
    </>
  )
}

function Contenido({ perfil, solicitud, ofertas, onCambio }) {
  const toast = useToast()
  const [creando, setCreando] = useState(false)
  const hayConvocatoria = ofertas.length > 0

  if (!perfil.limites.listo_para_carreras && !solicitud) {
    return (
      <Alert
        tone="warning"
        title="Completa tu perfil primero"
        action={
          <Button as={Link} to="/aspirante/completar-perfil" size="sm">
            Completar perfil
          </Button>
        }
      >
        Para seleccionar carreras necesitas tu foto, tu centro de trabajo, tu índice académico y los documentos obligatorios.
      </Alert>
    )
  }

  if (!solicitud) {
    async function crear() {
      setCreando(true)
      try {
        onCambio(await solicitudes.crear())
      } catch (e) {
        toast.error(mensajeDeError(e))
      } finally {
        setCreando(false)
      }
    }
    return (
      <EmptyState
        icon={FilePlus2}
        title={hayConvocatoria ? 'Aún no tienes una solicitud' : 'No hay una convocatoria abierta'}
        message={
          hayConvocatoria
            ? 'Crea tu solicitud para elegir las carreras a las que quieres optar.'
            : 'Te avisaremos cuando se abra la convocatoria de solicitud de matrícula.'
        }
        action={
          hayConvocatoria && (
            <Button icon={Plus} loading={creando} onClick={crear}>
              Nueva solicitud
            </Button>
          )
        }
      />
    )
  }

  // La key reinicia la selección local cuando llega una versión guardada.
  return <Editor key={`${solicitud.id}-${solicitud.modificada_at}-${solicitud.estado}`} perfil={perfil} solicitud={solicitud} ofertas={ofertas} onCambio={onCambio} />
}

function Editor({ perfil, solicitud, ofertas, onCambio }) {
  const toast = useToast()
  const guardada = useMemo(() => solicitud.carreras.map((c) => c.oferta), [solicitud])
  const [seleccion, setSeleccion] = useState(guardada)
  const [catalogo, setCatalogo] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')

  const editable = solicitud.editable && !perfil.bloqueado
  const maximo = solicitud.max_carreras
  const sinGuardar = seleccion.map((o) => o.id).join() !== guardada.map((o) => o.id).join()
  const esBorrador = solicitud.estado === 'borrador'
  const { convocatoria } = solicitud

  const agregar = useCallback((oferta) => setSeleccion((s) => [...s, oferta]), [])

  async function ejecutar(accion, mensaje) {
    setOcupado(true)
    setError('')
    try {
      onCambio(await accion())
      toast.exito(mensaje)
      return true
    } catch (e) {
      setError(mensajeDeError(e))
      return false
    } finally {
      setOcupado(false)
    }
  }

  const guardar = () =>
    ejecutar(() => solicitudes.guardarCarreras(solicitud.id, seleccion.map((o) => o.id)), 'Tu selección se guardó.')

  async function confirmar() {
    const ok = await ejecutar(() => solicitudes.confirmar(solicitud.id), 'Tu solicitud se confirmó. Te enviamos el resumen por correo.')
    if (ok) setConfirmando(false)
  }

  return (
    <div className={styles.pila}>
      <Card>
        <CardBody>
          <div className={styles.resumenSolicitud}>
            <div>
              <strong>
                Convocatoria {convocatoria.numero}.ª · curso {convocatoria.anio_academico}
              </strong>
              <p className={styles.ayuda}>
                {convocatoria.acepta_solicitudes
                  ? `Puedes modificarla hasta el ${formatearFecha(convocatoria.fecha_cierre)}.`
                  : 'La convocatoria cerró: esta es la versión que se tendrá en cuenta.'}
              </p>
            </div>
            <StatusBadge estado={solicitud.estado} mapa={ESTADOS_SOLICITUD} />
          </div>
          <dl className={styles.fechas}>
            <dt>Creada</dt>
            <dd>{formatearFechaHora(solicitud.created_at)}</dd>
            <dt>Confirmada</dt>
            <dd>{solicitud.confirmada_at ? formatearFechaHora(solicitud.confirmada_at) : 'Sin confirmar'}</dd>
            <dt>Última modificación</dt>
            <dd>{solicitud.modificada_at ? formatearFechaHora(solicitud.modificada_at) : '—'}</dd>
          </dl>
        </CardBody>
      </Card>

      {error && <Alert tone="danger">{error}</Alert>}
      {esBorrador && editable && (
        <Alert tone="info">
          Tu solicitud está en borrador: no participa hasta que la confirmes. Después de confirmarla podrás seguir cambiándola mientras la
          convocatoria esté abierta.
        </Alert>
      )}

      <Card>
        <CardHeader
          title={`Carreras seleccionadas (${seleccion.length} de ${maximo})`}
          actions={
            editable && (
              <Button size="sm" icon={Plus} onClick={() => setCatalogo(true)} disabled={seleccion.length >= maximo}>
                Agregar carrera
              </Button>
            )
          }
        />
        <CardBody>
          {seleccion.length === 0 ? (
            <p className={styles.ayuda}>Todavía no elegiste ninguna carrera.</p>
          ) : (
            <ListaOrdenable
              label="Carreras por orden de prioridad"
              items={seleccion}
              getKey={(o) => o.id}
              etiqueta={(o) => `${o.carrera_nombre} en ${o.entidad_nombre}`}
              onChange={setSeleccion}
              disabled={!editable}
              renderItem={(oferta, i) => <FilaCarrera oferta={oferta} indice={i} estado={solicitud.carreras.find((c) => c.oferta.id === oferta.id)} />}
              acciones={(oferta) =>
                editable && (
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={X}
                    aria-label={`Quitar ${oferta.carrera_nombre} en ${oferta.entidad_nombre}`}
                    onClick={() => setSeleccion((s) => s.filter((o) => o.id !== oferta.id))}
                  >
                    Quitar
                  </Button>
                )
              }
            />
          )}
          {editable && seleccion.length > 1 && (
            <p className={styles.ayuda}>Arrastra las carreras, usa las flechas o el teclado sobre el asa para cambiar la prioridad.</p>
          )}
        </CardBody>
      </Card>

      {editable && (
        <div className={styles.barraAcciones}>
          {sinGuardar && <span className={styles.ayuda}>Tienes cambios sin guardar.</span>}
          <Button variant="secondary" icon={Save} onClick={guardar} loading={ocupado && !confirmando} disabled={!sinGuardar}>
            Guardar cambios
          </Button>
          {esBorrador && (
            <Button icon={Send} onClick={() => setConfirmando(true)} disabled={sinGuardar || seleccion.length === 0 || ocupado}>
              Confirmar solicitud
            </Button>
          )}
        </div>
      )}

      <Catalogo
        open={catalogo}
        onClose={() => setCatalogo(false)}
        ofertas={ofertas}
        seleccion={seleccion}
        maximo={maximo}
        onAgregar={agregar}
      />
      <ConfirmDialog
        open={confirmando}
        title="Confirmar solicitud"
        message="Presentarás oficialmente tu solicitud con estas carreras y en este orden. Podrás modificarla hasta el cierre de la convocatoria."
        confirmLabel="Confirmar solicitud"
        tone="primary"
        loading={ocupado}
        onConfirm={confirmar}
        onCancel={() => setConfirmando(false)}
      />
    </div>
  )
}

function FilaCarrera({ oferta, indice, estado }) {
  return (
    <div className={styles.filaCarrera}>
      <span className={styles.prioridad} aria-hidden="true">
        {indice + 1}
      </span>
      <div>
        <span className={styles.ordinal}>{ORDINALES[indice] ?? `${indice + 1}.ª`} opción</span>
        <strong className={styles.carrera}>{oferta.carrera_nombre}</strong>
        <span className={styles.ayuda}>
          {oferta.entidad_nombre} · {oferta.municipio} · {oferta.duracion_anios} años
        </span>
      </div>
      {estado && estado.estado !== 'pendiente' && <span className={styles.estadoCarrera}>{estado.estado_nombre}</span>}
    </div>
  )
}

function Catalogo({ open, onClose, ofertas, seleccion, maximo, onAgregar }) {
  const [texto, setTexto] = useState('')
  const [tipo, setTipo] = useState('')
  const filtradas = ofertas.filter(
    (o) =>
      (!tipo || o.tipo_entidad === tipo) &&
      `${o.carrera_nombre} ${o.entidad_nombre} ${o.municipio}`.toLowerCase().includes(texto.trim().toLowerCase()),
  )

  return (
    <Modal open={open} onClose={onClose} title="Agregar carrera" description="Carreras con plazas en esta convocatoria." size="lg">
      <div className={styles.filtrosCatalogo}>
        <Input label="Buscar" placeholder="Carrera, entidad o municipio" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <Select
          label="Tipo de entidad"
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          placeholder="Todas"
          options={Object.entries(TIPOS).map(([value, label]) => ({ value, label }))}
        />
      </div>
      {filtradas.length === 0 ? (
        <p className={styles.ayuda}>No hay carreras que coincidan.</p>
      ) : (
        <ul className={styles.catalogo}>
          {filtradas.map((oferta) => {
            const motivo = motivoNoDisponible(oferta, seleccion, maximo)
            return (
              <li key={oferta.id} className={styles.ofertaCatalogo}>
                <div>
                  <strong>{oferta.carrera_nombre}</strong>
                  <span className={styles.ayuda}>
                    {TIPOS[oferta.tipo_entidad]}: {oferta.entidad_nombre} · {oferta.municipio} · {oferta.plazas} plazas
                  </span>
                  {motivo && <span className={styles.motivo}>{motivo}</span>}
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={Plus}
                  disabled={Boolean(motivo)}
                  aria-label={`Agregar ${oferta.carrera_nombre} en ${oferta.entidad_nombre}`}
                  onClick={() => onAgregar(oferta)}
                >
                  Agregar
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </Modal>
  )
}
