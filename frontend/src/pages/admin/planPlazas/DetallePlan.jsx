import { ArrowLeft, CheckCircle2, CopyPlus, Download, FileSpreadsheet, FileText, Send, SkipForward, Undo2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { RecursoModal } from '../../../components/crud/RecursoModal'
import {
  Alert,
  Badge,
  BotonConfirmado,
  Button,
  Card,
  CardBody,
  CardHeader,
  PageHeader,
  Spinner,
  StatusBadge,
  Stepper,
  Tabs,
  useToast,
} from '../../../components/ui'
import { mensajeDeError } from '../../../services/errores'
import { lineasPlan, planes } from '../../../services/planPlazas'
import { descargarBlob } from '../../../utils/descargar'
import { formatearFechaHora } from '../../../utils/fechas'
import { ComentariosPlan } from './ComentariosPlan'
import { ESTADO_ENTIDAD, ESTADO_PLAN, pasosDe } from './estados'
import { HistorialPlan } from './HistorialPlan'
import { LineasPlan } from './LineasPlan'
import styles from './Plan.module.css'

const TABS = [
  { id: 'lineas', label: 'Carreras y plazas' },
  { id: 'comentarios', label: 'Comentarios' },
  { id: 'historial', label: 'Historial' },
]

/** Qué tiene que hacer cada quien en este estado (RG-002: el usuario sabe siempre el siguiente paso). */
function ayuda(plan) {
  const a = new Set(plan.acciones)
  if (a.has('enviar')) return 'Arma la propuesta inicial y envíala a las Facultades y CUM/FUM.'
  if (a.has('responder')) return 'Revisa las carreras de tu entidad: acepta, ajusta las cantidades, pide quitar o agrega carreras, y envía tu propuesta.'
  if (a.has('cerrar_revision')) return 'Las entidades están revisando. Cuando todas envíen su propuesta, pasa a la revisión de la CI (o fuérzalo).'
  if (a.has('decidir')) return 'Decide el valor final de cada carrera. Si no cambias una línea, se acepta lo que propuso la entidad.'
  if (a.has('aprobar')) return 'Revisa la versión final. Al aprobarla, el plan queda publicado.'
  return null
}

function Entidades({ entidades }) {
  if (entidades.length === 0) return null
  return (
    <Card>
      <CardHeader title="Entidades" />
      <CardBody>
        <ul className={styles.entidades}>
          {entidades.map((e) => (
            <li key={e.id}>
              <span>{e.entidad.nombre}</span>
              <StatusBadge estado={e.estado} mapa={ESTADO_ENTIDAD} />
              {e.enviada_at && <small>{`${e.enviada_por_nombre} · ${formatearFechaHora(e.enviada_at)}`}</small>}
              {e.comentario && <small className={styles.comentarioEntidad}>“{e.comentario}”</small>}
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}

/** Detalle y flujo de un plan de plazas (sección 7.3). */
export function DetallePlan() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [plan, setPlan] = useState(null)
  const [lineas, setLineas] = useState([])
  const [error, setError] = useState('')
  const [tab, setTab] = useState('lineas')
  const [modalTexto, setModalTexto] = useState(null) // 'devolver' | 'propuesta' | 'complementaria'
  const [version, setVersion] = useState(0)

  // Plan y líneas se cargan juntos; `cargar()` pide una recarga tras cada acción.
  useEffect(() => {
    let vigente = true
    Promise.all([planes.obtener(id), lineasPlan.listar(id)])
      .then(([datosPlan, datosLineas]) => {
        if (!vigente) return
        setPlan(datosPlan)
        setLineas(datosLineas)
        setError('')
      })
      .catch((err) => vigente && setError(mensajeDeError(err)))
    return () => {
      vigente = false
    }
  }, [id, version])

  const cargar = useCallback(() => setVersion((v) => v + 1), [])

  async function ejecutar(accion, mensaje) {
    try {
      await accion()
      toast.exito(mensaje)
      cargar()
    } catch (err) {
      toast.error(mensajeDeError(err))
    }
  }

  async function exportar(funcion, extension) {
    try {
      descargarBlob(await funcion(plan.id), `plan-plazas-${plan.anio_academico}-v${plan.version}.${extension}`)
    } catch (err) {
      toast.error(mensajeDeError(err))
    }
  }

  if (error && !plan) return <Alert tone="danger">{error}</Alert>
  if (!plan) return <Spinner label="Cargando el plan" />

  const a = new Set(plan.acciones)
  const pendientes = plan.entidades.filter((e) => e.estado !== 'propuesta_enviada').length
  const textoAyuda = ayuda(plan)

  const modales = {
    devolver: {
      titulo: 'Devolver el plan a la Comisión de Ingreso',
      campos: [{ name: 'texto', label: 'Observaciones', type: 'textarea', required: true }],
      validar: (v) => (v.texto.trim() ? {} : { texto: 'Escribe las observaciones.' }),
      guardar: (v) => planes.devolver(plan.id, v.texto),
      mensaje: 'El plan volvió a la Comisión de Ingreso.',
    },
    propuesta: {
      titulo: 'Enviar la propuesta de la entidad',
      campos: [{ name: 'texto', label: 'Comentario general (opcional)', type: 'textarea' }],
      validar: () => ({}),
      guardar: (v) => planes.enviarPropuesta(plan.id, v.texto),
      mensaje: 'Tu propuesta se envió a la Comisión de Ingreso.',
    },
    complementaria: {
      titulo: 'Crear versión complementaria',
      campos: [{ name: 'texto', label: 'Motivo', type: 'textarea', hint: 'Parte de las plazas aprobadas vigentes y tiene su propio flujo de aprobación (RF-039).' }],
      validar: () => ({}),
      guardar: (v) => planes.complementaria(plan.id, v.texto),
      mensaje: 'Se creó la versión complementaria.',
    },
  }
  const modal = modalTexto && modales[modalTexto]

  return (
    <>
      <Button as={Link} to="/admin/plan-plazas" variant="link" icon={ArrowLeft}>
        Volver a los planes
      </Button>
      <PageHeader
        title={`Plan de plazas ${plan.anio_academico}`}
        subtitle={
          <>
            <StatusBadge estado={plan.estado} mapa={ESTADO_PLAN} /> {plan.es_complementario && <Badge tone="info">Versión complementaria</Badge>}{' '}
            {plan.version > 0 && `Versión ${plan.version}`}
            {plan.fecha_aprobacion && ` · Aprobado por ${plan.aprobado_por_nombre} el ${formatearFechaHora(plan.fecha_aprobacion)}`}
          </>
        }
        actions={
          <div className={styles.acciones}>
            {a.has('cargar_oferta') && (
              <Button variant="secondary" icon={Download} onClick={() => ejecutar(() => planes.cargarOferta(plan.id), 'Se cargó la oferta del año.')}>
                Cargar oferta del año
              </Button>
            )}
            {a.has('enviar') && (
              <BotonConfirmado
                icon={Send}
                titulo="Enviar a las entidades"
                mensaje="Las Facultades y CUM/FUM podrán revisar la propuesta. El borrador dejará de poder editarse."
                onConfirm={() => ejecutar(() => planes.enviar(plan.id), 'El plan se envió a las entidades.')}
              >
                Enviar a las entidades
              </BotonConfirmado>
            )}
            {a.has('enviar_propuesta') && (
              <Button icon={Send} onClick={() => setModalTexto('propuesta')}>
                Enviar propuesta
              </Button>
            )}
            {a.has('cerrar_revision') && (
              <BotonConfirmado
                icon={SkipForward}
                variant={pendientes ? 'secondary' : 'primary'}
                titulo="Pasar a la revisión de la CI"
                mensaje={
                  pendientes
                    ? `Faltan ${pendientes} entidad(es) por enviar su propuesta. Si continúas, conservarán la propuesta inicial de la CI.`
                    : 'Todas las entidades enviaron su propuesta.'
                }
                confirmLabel={pendientes ? 'Forzar y continuar' : 'Continuar'}
                onConfirm={() => ejecutar(() => planes.cerrarRevision(plan.id, pendientes > 0), 'El plan pasó a la revisión de la CI.')}
              >
                Pasar a revisión de la CI
              </BotonConfirmado>
            )}
            {a.has('generar_version_final') && (
              <BotonConfirmado
                icon={CheckCircle2}
                titulo="Generar versión final"
                mensaje="Se fijarán las plazas de cada carrera y el plan pasará al Vicerrector para su aprobación."
                onConfirm={() => ejecutar(() => planes.generarVersionFinal(plan.id), 'La versión final se envió al Vicerrector.')}
              >
                Generar versión final
              </BotonConfirmado>
            )}
            {a.has('devolver') && (
              <Button variant="secondary" icon={Undo2} onClick={() => setModalTexto('devolver')}>
                Devolver
              </Button>
            )}
            {a.has('aprobar') && (
              <BotonConfirmado
                icon={CheckCircle2}
                variant="success"
                tone="success"
                titulo="Aprobar y publicar"
                mensaje="El plan quedará publicado y no se podrá modificar (RF-039). Se fijarán las plazas de la oferta."
                onConfirm={() => ejecutar(() => planes.aprobar(plan.id), 'El plan se aprobó y publicó.')}
              >
                Aprobar y publicar
              </BotonConfirmado>
            )}
            {a.has('exportar') && (
              <>
                <Button variant="secondary" icon={FileText} onClick={() => exportar(planes.exportarPdf, 'pdf')}>
                  PDF
                </Button>
                <Button variant="secondary" icon={FileSpreadsheet} onClick={() => exportar(planes.exportarExcel, 'xlsx')}>
                  Excel
                </Button>
              </>
            )}
            {a.has('crear_complementaria') && (
              <Button variant="secondary" icon={CopyPlus} onClick={() => setModalTexto('complementaria')}>
                Versión complementaria
              </Button>
            )}
          </div>
        }
      />

      <div className={styles.pila}>
        <Card>
          <CardBody>
            <Stepper steps={pasosDe(plan.estado)} label="Estado del plan" />
          </CardBody>
        </Card>
        {plan.observaciones_vicerrector && plan.estado === 'revision_ci' && (
          <Alert tone="warning" title="Devuelto por el Vicerrector">
            {plan.observaciones_vicerrector}
          </Alert>
        )}
        {textoAyuda && <Alert tone="info">{textoAyuda}</Alert>}
        {plan.estado !== 'borrador' && <Entidades entidades={plan.entidades} />}

        <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Contenido del plan">
          {tab === 'lineas' && (
            <Card>
              <LineasPlan plan={plan} lineas={lineas} onCambio={cargar} />
            </Card>
          )}
          {tab === 'comentarios' && <ComentariosPlan plan={plan} />}
          {tab === 'historial' && (
            <Card>
              <HistorialPlan plan={plan} />
            </Card>
          )}
        </Tabs>
      </div>

      {modal && (
        <RecursoModal
          key={modalTexto}
          open
          titulo={modal.titulo}
          campos={modal.campos}
          valoresIniciales={{ texto: '' }}
          validar={modal.validar}
          onGuardar={modal.guardar}
          onClose={(resultado) => {
            setModalTexto(null)
            if (!resultado) return
            toast.exito(modal.mensaje)
            if (modalTexto === 'complementaria') navigate(`/admin/plan-plazas/${resultado.id}`)
            else cargar()
          }}
        />
      )}
    </>
  )
}
