import { ArrowLeft, CheckCircle2, Eye, Send, XCircle } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Alert, BotonConfirmado, Button, Card, CardBody, CardHeader, Modal, PageHeader, Spinner, StatusBadge, Textarea, useToast } from '../../../components/ui'
import { useCarga } from '../../../hooks/useCarga'
import { mensajeDeError } from '../../../services/errores'
import { prematriculasAdmin } from '../../../services/prematricula'
import { formatearTamano } from '../../../utils/archivos'
import { ESTADOS_PREMATRICULA, REVISION_ELEMENTO } from '../../../utils/estadosPrematricula'
import { formatearFechaHora } from '../../../utils/fechas'
import { VisorDocumento } from '../solicitudes/VisorDocumento'
import styles from './Prematricula.module.css'

/** Revisión de un expediente de prematrícula, documento por documento (RF-069). */
export function DetallePrematricula() {
  const { id } = useParams()
  const toast = useToast()
  const cargar = useCallback(() => prematriculasAdmin.obtener(id), [id])
  const carga = useCarga(cargar)
  const [actualizada, setActualizada] = useState(null)
  const [viendo, setViendo] = useState(null)
  const [rechazando, setRechazando] = useState(null)
  const prematricula = actualizada ?? carga.datos

  if (carga.cargando) return <Spinner label="Cargando el expediente" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const { permisos } = prematricula

  async function ejecutar(accion, mensaje) {
    try {
      setActualizada(await accion())
      if (mensaje) toast.exito(mensaje)
    } catch (e) {
      toast.error(mensajeDeError(e))
    }
  }

  const aprobarElemento = (e) => ejecutar(() => prematriculasAdmin.revisar(prematricula.id, e.id, 'aprobado'))

  return (
    <>
      <PageHeader
        title={prematricula.aspirante_nombre}
        subtitle={`Prematrícula de ${prematricula.carrera} — ${prematricula.entidad}`}
        actions={
          <Button as={Link} to="/admin/prematricula" variant="ghost" icon={ArrowLeft}>
            Volver
          </Button>
        }
      />
      <div className={styles.pila}>
        <div className={styles.resumen}>
          <StatusBadge estado={prematricula.estado} mapa={ESTADOS_PREMATRICULA} />
          {prematricula.enviada_at && <span className={styles.apagado}>Enviada el {formatearFechaHora(prematricula.enviada_at)}</span>}
          {prematricula.fecha_aprobacion && (
            <span className={styles.apagado}>
              Aprobada el {formatearFechaHora(prematricula.fecha_aprobacion)} por {prematricula.aprobado_por}
            </span>
          )}
        </div>
        {!permisos.revisar && prematricula.estado !== 'aprobada' && (
          <Alert tone="info">Se revisa cuando el aspirante la envía. Ahora está en estado «{prematricula.estado_nombre}».</Alert>
        )}
        {!permisos.descargar && <Alert tone="info">Tu rol no tiene permiso para abrir los documentos personales del aspirante.</Alert>}

        <Card>
          <CardHeader title="Documentos y campos" />
          <CardBody>
            <ul className={styles.elementos}>
              {prematricula.elementos.map((e) => (
                <li key={e.id}>
                  <div className={styles.elementoInfo}>
                    <strong>{e.nombre}</strong>
                    <StatusBadge estado={e.revision} mapa={REVISION_ELEMENTO} />
                    {e.tipo === 'documento_perfil' && <span className={styles.apagado}>Del perfil del aspirante</span>}
                    <span className={styles.apagado}>
                      {e.tipo === 'texto'
                        ? e.valor_texto || 'Sin completar'
                        : e.archivo
                          ? `${e.archivo.nombre_original} · v${e.archivo.version} · ${formatearTamano(e.archivo.tamano)}`
                          : e.requerido
                            ? 'Sin entregar'
                            : 'Sin entregar (opcional)'}
                    </span>
                    {e.revision === 'rechazado' && <span className={styles.observacion}>Observación: {e.observacion}</span>}
                  </div>
                  <div className={styles.acciones}>
                    {e.archivo && permisos.descargar && (
                      <Button variant="ghost" size="sm" icon={Eye} onClick={() => setViendo(e)} aria-label={`Ver ${e.nombre}`}>
                        Ver
                      </Button>
                    )}
                    {permisos.revisar && e.entregado && (
                      <>
                        <Button variant="secondary" size="sm" icon={CheckCircle2} onClick={() => aprobarElemento(e)} aria-label={`Aprobar ${e.nombre}`}>
                          Aprobar
                        </Button>
                        <Button variant="ghost" size="sm" icon={XCircle} onClick={() => setRechazando(e)} aria-label={`Rechazar ${e.nombre}`}>
                          Rechazar
                        </Button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        {permisos.revisar && (
          <div className={styles.barra}>
            <BotonConfirmado
              variant="secondary"
              icon={Send}
              titulo="Solicitar correcciones"
              mensaje="Se avisará al aspirante con lo rechazado y sus observaciones. No pierde la plaza."
              onConfirm={() => ejecutar(() => prematriculasAdmin.solicitarCorrecciones(prematricula.id), 'Se pidieron las correcciones.')}
            >
              Solicitar correcciones
            </BotonConfirmado>
            <BotonConfirmado
              icon={CheckCircle2}
              titulo="Aprobar prematrícula"
              mensaje="Todos los documentos requeridos deben estar aprobados. Se avisará al aspirante."
              onConfirm={() => ejecutar(() => prematriculasAdmin.aprobar(prematricula.id), 'Prematrícula aprobada.')}
            >
              Aprobar prematrícula
            </BotonConfirmado>
          </div>
        )}
      </div>
      <VisorDocumento
        documento={viendo?.archivo}
        titulo={viendo?.nombre}
        onClose={() => setViendo(null)}
      />
      {rechazando && (
        <Rechazar
          elemento={rechazando}
          onClose={() => setRechazando(null)}
          onRechazar={(observacion) => ejecutar(() => prematriculasAdmin.revisar(prematricula.id, rechazando.id, 'rechazado', observacion))}
        />
      )}
    </>
  )
}

function Rechazar({ elemento, onClose, onRechazar }) {
  const [observacion, setObservacion] = useState('')
  return (
    <Modal
      open
      onClose={onClose}
      title={`Rechazar: ${elemento.nombre}`}
      description="El aspirante podrá corregir solo lo rechazado, incluso después del cierre."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            disabled={!observacion.trim()}
            onClick={async () => {
              await onRechazar(observacion.trim())
              onClose()
            }}
          >
            Rechazar
          </Button>
        </>
      }
    >
      <Textarea label="Observación" required rows={3} maxLength={2000} value={observacion} onChange={(e) => setObservacion(e.target.value)} />
    </Modal>
  )
}
