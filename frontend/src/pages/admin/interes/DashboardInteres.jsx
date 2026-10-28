import { Lightbulb } from 'lucide-react'
import { useCallback, useState } from 'react'
import { BarrasHorizontales, EvolucionDiaria } from '../../../components/graficos/Graficos'
import { MapaMunicipios } from '../../../components/graficos/MapaMunicipios'
import { Alert, Card, CardBody, CardHeader, EmptyState, KpiCard, Spinner } from '../../../components/ui'
import { usePolling } from '../../../hooks/usePolling'
import { mensajeDeError } from '../../../services/errores'
import { expresiones } from '../../../services/interes'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Interes.module.css'

/**
 * Dashboard de interés (RF-029). Cada rol ve su ámbito (RF-030). Se actualiza
 * cada 60 s con la pestaña visible. Por entidad se usan barras ordenadas en
 * lugar del pastel de la ERS (decisión del cliente: con muchas entidades el
 * pastel no se lee).
 */
export function DashboardInteres({ convocatoria }) {
  const [estado, setEstado] = useState({ datos: null, error: '', actualizado: null })
  const actualizar = useCallback(() => {
    expresiones
      .estadisticas({ convocatoria: convocatoria.id })
      .then((datos) => setEstado({ datos, error: '', actualizado: new Date().toISOString() }))
      .catch((error) => setEstado((e) => ({ ...e, error: mensajeDeError(error) })))
  }, [convocatoria.id])
  usePolling(actualizar)

  const { datos } = estado
  if (!datos) return estado.error ? <Alert tone="danger">{estado.error}</Alert> : <Spinner label="Cargando el dashboard de interés" />

  return (
    <div className={styles.pila}>
      <p className={styles.apagado}>Actualizado {formatearFechaHora(estado.actualizado)}</p>
      <div className={styles.kpis}>
        <KpiCard label="Expresiones de interés" value={datos.total} icon={Lightbulb} hint={`Convocatoria ${convocatoria.anio_academico}`} />
        <KpiCard label="Carreras con interés" value={datos.por_carrera.length} />
        <KpiCard label="Municipios con interés" value={datos.por_municipio.filter((m) => m.total > 0).length} hint="de 14" />
      </div>
      {datos.total === 0 ? (
        <EmptyState title="Todavía no hay expresiones de interés" message="Los gráficos aparecen cuando la población expresa interés en la landing." />
      ) : (
        <>
          <div className={styles.dosColumnas}>
            <Card>
              <CardHeader title="Por carrera" />
              <CardBody>
                <BarrasHorizontales unidad="expresiones" filas={datos.por_carrera.map((f) => ({ clave: f.carrera, etiqueta: f.carrera, valor: f.total }))} />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Por Facultad / CUM-FUM" />
              <CardBody>
                <BarrasHorizontales unidad="expresiones" filas={datos.por_entidad.map((f) => ({ clave: f.entidad, etiqueta: f.entidad, valor: f.total }))} />
              </CardBody>
            </Card>
          </div>
          <Card>
            <CardHeader title="Evolución diaria" />
            <CardBody>
              <EvolucionDiaria titulo="Expresiones de interés por día" unidad="expresiones" puntos={datos.evolucion} />
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Distribución territorial" />
            <CardBody>
              <MapaMunicipios titulo="Interés por municipio" filas={datos.por_municipio} />
            </CardBody>
          </Card>
        </>
      )}
    </div>
  )
}
