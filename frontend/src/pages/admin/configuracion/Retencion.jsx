import { ShieldCheck } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Alert, BotonConfirmado, Card, CardBody, CardHeader, DataTable, Spinner, useToast } from '../../../components/ui'
import { useCarga } from '../../../hooks/useCarga'
import { retencion } from '../../../services/configuracion'
import { mensajeDeError } from '../../../services/errores'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Configuracion.module.css'

const COLUMNAS = [
  { key: 'fecha', header: 'Fecha', render: (e) => formatearFechaHora(e.fecha) },
  { key: 'tipo', header: 'Tipo', render: (e) => (e.automatica ? 'Automática' : `Manual · ${e.ejecutada_por ?? '—'}`) },
  { key: 'aspirantes_anonimizados', header: 'Aspirantes', align: 'right' },
  { key: 'intereses_anonimizados', header: 'Intereses', align: 'right' },
  { key: 'documentos_eliminados', header: 'Archivos', align: 'right' },
  { key: 'espacio_liberado_mb', header: 'MB liberados', align: 'right' },
  { key: 'duracion_segundos', header: 'Segundos', align: 'right' },
]

const cargar = () => Promise.all([retencion.previsualizar(), retencion.ejecuciones()])

/**
 * Retención de datos (RG-028): qué se anonimizaría hoy, ejecución adelantada y
 * historial. La tarea mensual la ejecuta sola; los registros de auditoría no se alteran.
 */
export function Retencion({ editable }) {
  const toast = useToast()
  const carga = useCarga(cargar)
  const [actualizado, setActualizado] = useState(null)
  const datos = actualizado ?? carga.datos

  const ejecutar = useCallback(async () => {
    try {
      const ejecucion = await retencion.ejecutar()
      setActualizado(await cargar())
      toast.exito(`Retención aplicada: ${ejecucion.aspirantes_anonimizados} aspirantes y ${ejecucion.intereses_anonimizados} expresiones de interés anonimizados.`)
    } catch (e) {
      toast.error(mensajeDeError(e))
    }
  }, [toast])

  if (carga.cargando) return <Spinner label="Calculando la retención" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const [vista, ejecuciones] = datos
  const nada = vista.aspirantes + vista.intereses + vista.documentos === 0

  return (
    <div className={styles.pila}>
      <Card>
        <CardHeader title="Qué haría una ejecución hoy" />
        <CardBody>
          <p className={styles.descripcion}>
            La política se aplica sola el día 1 de cada mes. Anonimiza a los no seleccionados y las expresiones de interés pasados los años de
            retención, y a los otorgados pasada la retención ampliada. Borra sus archivos y las versiones antiguas de documentos. Conserva
            solicitudes, resultados y estadísticas. Los registros de auditoría no se alteran.
          </p>
          <dl className={styles.resumenRetencion}>
            <div><dt>Aspirantes a anonimizar</dt><dd>{vista.aspirantes}</dd></div>
            <div><dt>Expresiones de interés a anonimizar</dt><dd>{vista.intereses}</dd></div>
            <div><dt>Archivos que se eliminan</dt><dd>{vista.documentos}</dd></div>
            <div><dt>Espacio estimado liberado</dt><dd>{vista.espacio_mb} MB</dd></div>
            <div><dt>Expedientes con solo versiones antiguas a borrar</dt><dd>{vista.solo_versiones_antiguas}</dd></div>
          </dl>
          {editable && (
            <BotonConfirmado
              icon={ShieldCheck}
              tone="danger"
              titulo="Ejecutar la retención ahora"
              mensaje="Se anonimizarán los datos personales y se borrarán los archivos indicados. No se puede deshacer."
              confirmLabel="Ejecutar"
              disabled={nada}
              onConfirm={ejecutar}
            >
              Ejecutar ahora
            </BotonConfirmado>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Ejecuciones" />
        <DataTable columns={COLUMNAS} rows={ejecuciones} emptyMessage="Todavía no se ejecutó la retención." />
      </Card>
    </div>
  )
}
