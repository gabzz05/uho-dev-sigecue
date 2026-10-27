import { Play } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Alert, Button, Card, CardBody, CardHeader, Checkbox, Modal, PageHeader, Select, Spinner, useToast } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useCarga } from '../../../hooks/useCarga'
import { convocatoriasSolicitud } from '../../../services/convocatorias'
import { mensajeDeError } from '../../../services/errores'
import { otorgamientos } from '../../../services/otorgamiento'
import { DetalleOtorgamiento } from './DetalleOtorgamiento'
import styles from './Otorgamiento.module.css'

const etiqueta = (c) => `${c.numero}.ª convocatoria ${c.anio_academico}`

/** Otorgamiento de plazas (sección 5.9): generar, revisar, ajustar, aprobar y publicar. */
export function Otorgamiento() {
  const { tienePermiso } = useAuth()
  const puedeGenerar = tienePermiso('otorgamiento.generar')
  const cargar = useCallback(
    () =>
      Promise.all([
        otorgamientos.listar(),
        puedeGenerar ? convocatoriasSolicitud.listar({ page_size: 100 }).then((r) => r.results) : Promise.resolve([]),
      ]),
    [puedeGenerar],
  )
  const carga = useCarga(cargar)
  const [generados, setGenerados] = useState([])
  const [elegido, setElegido] = useState('')

  if (carga.cargando) return <Spinner label="Cargando el otorgamiento" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const [lista, convocatorias] = carga.datos
  const todos = [...generados, ...lista.filter((o) => !generados.some((g) => g.id === o.id))]
  const conOtorgamiento = new Set(todos.map((o) => o.convocatoria.id))
  const pendientes = convocatorias.filter((c) => c.estado === 'cerrada' && !conOtorgamiento.has(c.id))
  const actual = todos.find((o) => String(o.id) === elegido) ?? todos[0]

  function alGenerar(otorgamiento) {
    setGenerados((g) => [otorgamiento, ...g])
    setElegido(String(otorgamiento.id))
  }

  return (
    <>
      <PageHeader title="Otorgamiento" subtitle="Ranking por índice académico, reparto de plazas y publicación del resultado." />
      <div className={styles.pila}>
        {pendientes.map((c) => (
          <PendienteDeGenerar key={c.id} convocatoria={c} onGenerado={alGenerar} />
        ))}
        {todos.length === 0 ? (
          pendientes.length === 0 && (
            <Alert tone="info">
              {puedeGenerar
                ? 'No hay convocatorias cerradas pendientes de otorgamiento.'
                : 'Todavía no hay otorgamientos que puedas consultar. Las entidades ven el resultado cuando el Vicerrector lo publica.'}
            </Alert>
          )
        ) : (
          <>
            {todos.length > 1 && (
              <div className={styles.selector}>
                <Select
                  label="Convocatoria"
                  options={todos.map((o) => ({ value: String(o.id), label: etiqueta(o.convocatoria) }))}
                  value={String(actual.id)}
                  onChange={(e) => setElegido(e.target.value)}
                />
              </div>
            )}
            <DetalleOtorgamiento key={actual.id} inicial={actual} />
          </>
        )}
      </div>
    </>
  )
}

function PendienteDeGenerar({ convocatoria, onGenerado }) {
  const toast = useToast()
  const [resumen, setResumen] = useState(null)
  const [confirmado, setConfirmado] = useState(false)
  const [ocupado, setOcupado] = useState(false)

  async function previsualizar() {
    setOcupado(true)
    try {
      setResumen(await otorgamientos.previsualizar(convocatoria.id))
      setConfirmado(false)
    } catch (e) {
      toast.error(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  async function generar() {
    setOcupado(true)
    try {
      onGenerado(await otorgamientos.generar(convocatoria.id))
      toast.exito('Se generó el otorgamiento. Pasa a la revisión del Jefe de la Comisión de Ingreso.')
      setResumen(null)
    } catch (e) {
      toast.error(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  return (
    <Card>
      <CardHeader title={`${etiqueta(convocatoria)}: pendiente de otorgamiento`} />
      <CardBody>
        <p className={styles.apagado}>
          La convocatoria está cerrada. El otorgamiento se genera una sola vez: entran al ranking solo las solicitudes elegibles.
        </p>
        <Button icon={Play} onClick={previsualizar} loading={ocupado && !resumen}>
          Generar otorgamiento
        </Button>
      </CardBody>
      <Modal
        open={Boolean(resumen)}
        onClose={() => setResumen(null)}
        title="Generar otorgamiento"
        description={etiqueta(convocatoria)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setResumen(null)}>
              Cancelar
            </Button>
            <Button onClick={generar} disabled={!confirmado} loading={ocupado}>
              Generar
            </Button>
          </>
        }
      >
        {resumen && (
          <div className={styles.formulario}>
            <dl className={styles.datos}>
              <dt>Solicitudes confirmadas</dt>
              <dd>{resumen.solicitudes}</dd>
              <dt>Elegibles</dt>
              <dd>
                <strong>{resumen.elegibles}</strong>
              </dd>
              <dt>No elegibles</dt>
              <dd>{resumen.no_elegibles}</dd>
              <dt>Plazas disponibles</dt>
              <dd>{resumen.plazas}</dd>
            </dl>
            {resumen.motivos.length > 0 && (
              <>
                <strong>Motivos de exclusión</strong>
                <ul className={styles.motivos}>
                  {resumen.motivos.map((m) => (
                    <li key={m.motivo}>
                      {m.motivo}: {m.cantidad}
                    </li>
                  ))}
                </ul>
                <p className={styles.apagado}>Una solicitud puede tener varios motivos.</p>
              </>
            )}
            <Checkbox
              label="Entiendo que las solicitudes no elegibles quedan fuera y que el otorgamiento no se puede volver a generar."
              checked={confirmado}
              onChange={(e) => setConfirmado(e.target.checked)}
            />
          </div>
        )}
      </Modal>
    </Card>
  )
}
