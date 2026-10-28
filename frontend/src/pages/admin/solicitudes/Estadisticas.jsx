import { ClipboardList, FileWarning, Inbox, Search } from 'lucide-react'
import { useCallback, useState } from 'react'
import { BarrasHorizontales, EvolucionDiaria, Termometro } from '../../../components/graficos/Graficos'
import { Alert, Card, CardBody, CardHeader, EmptyState, KpiCard, Spinner } from '../../../components/ui'
import { usePolling } from '../../../hooks/usePolling'
import { mensajeDeError } from '../../../services/errores'
import { solicitudesAdmin } from '../../../services/solicitudes'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Solicitudes.module.css'

/** Estadísticas en tiempo casi real (RF-053): se actualizan cada 60 s con la pestaña visible. */
export function Estadisticas({ convocatoria }) {
  const [estado, setEstado] = useState({ clave: null, datos: null, error: '', actualizado: null })

  const actualizar = useCallback(() => {
    solicitudesAdmin
      .estadisticas(convocatoria ? { convocatoria } : {})
      .then((datos) => setEstado({ clave: convocatoria, datos, error: '', actualizado: new Date().toISOString() }))
      .catch((error) => setEstado((e) => ({ ...e, clave: convocatoria, error: mensajeDeError(error) })))
  }, [convocatoria])
  usePolling(actualizar)

  // Al cambiar de convocatoria no se muestran los datos de la anterior.
  if (estado.clave !== convocatoria) return <Spinner label="Cargando estadísticas" />
  if (estado.error && !estado.datos) return <Alert tone="danger">{estado.error}</Alert>

  const { datos } = estado
  if (!datos.convocatoria) {
    return (
      <EmptyState
        title="Todavía no hay convocatorias de solicitud"
        message="Las estadísticas aparecen cuando se abre la primera convocatoria de solicitud de matrícula."
      />
    )
  }
  const { totales } = datos
  const sinDatos = totales.solicitudes === 0

  return (
    <div className={styles.pila}>
      <p className={styles.apagado}>
        Convocatoria {datos.convocatoria.numero}.ª {datos.convocatoria.anio_academico} · actualizado {formatearFechaHora(estado.actualizado)}
      </p>
      <div className={styles.kpis}>
        <KpiCard label="Solicitudes" value={totales.solicitudes} icon={Inbox} hint={`Plazas del plan: ${totales.plazas}`} />
        <KpiCard label="Pendientes" value={totales.por_estado.pendiente} icon={ClipboardList} tone="warning" />
        <KpiCard label="En revisión" value={totales.por_estado.en_revision} icon={Search} tone="primary" />
        <KpiCard label="Observadas" value={totales.por_estado.observada} icon={FileWarning} tone="danger" />
      </div>

      {sinDatos ? (
        <EmptyState title="Todavía no hay solicitudes confirmadas" message="Las estadísticas aparecen cuando los aspirantes confirman sus solicitudes." />
      ) : (
        <>
          <Card>
            <CardHeader title="Solicitudes frente al plan de plazas" />
            <CardBody>
              <Termometro
                filas={datos.termometro.map((f) => ({
                  clave: f.oferta,
                  etiqueta: f.carrera,
                  detalle: `${f.entidad} · ${f.primera_opcion} en 1.ª opción`,
                  valor: f.solicitudes,
                  referencia: f.plazas,
                }))}
              />
            </CardBody>
          </Card>
          <div className={styles.dosColumnas}>
            <Card>
              <CardHeader title="Distribución por carrera" />
              <CardBody>
                <BarrasHorizontales
                  unidad="solicitudes"
                  filas={datos.por_carrera.map((f) => ({ clave: f.carrera, etiqueta: f.carrera, valor: f.solicitudes }))}
                />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Evolución diaria" />
              <CardBody>
                <EvolucionDiaria titulo="Solicitudes confirmadas por día" unidad="solicitudes" puntos={datos.evolucion} />
              </CardBody>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
