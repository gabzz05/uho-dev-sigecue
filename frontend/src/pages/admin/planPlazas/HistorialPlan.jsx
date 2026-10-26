import { useCallback } from 'react'
import { Alert, DataTable } from '../../../components/ui'
import { useCarga } from '../../../hooks/useCarga'
import { planes } from '../../../services/planPlazas'
import { formatearFechaHora } from '../../../utils/fechas'

const COLUMNAS = [
  { key: 'created_at', header: 'Fecha', render: (h) => formatearFechaHora(h.created_at) },
  { key: 'version', header: 'Versión', align: 'center', render: (h) => h.version || '—' },
  { key: 'usuario_nombre', header: 'Usuario' },
  { key: 'accion', header: 'Acción' },
  { key: 'descripcion_linea', header: 'Carrera / entidad', render: (h) => h.descripcion_linea || '—' },
  {
    key: 'cambio',
    header: 'Cambio',
    render: (h) => (h.valor_anterior || h.valor_nuevo ? `${h.valor_anterior || '—'} → ${h.valor_nuevo || '—'}` : '—'),
  },
  { key: 'comentario', header: 'Comentario', render: (h) => h.comentario || '—' },
]

/** Historial de cambios del plan (RF-038). */
export function HistorialPlan({ plan }) {
  // `plan` cambia con cada acción: el historial se recarga solo.
  const carga = useCarga(useCallback(() => planes.historial(plan.id), [plan]))
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>
  return <DataTable columns={COLUMNAS} rows={carga.datos ?? []} loading={carga.cargando} emptyMessage="Sin cambios registrados." />
}
