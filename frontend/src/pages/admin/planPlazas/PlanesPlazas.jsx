import { Eye, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { RecursoModal } from '../../../components/crud/RecursoModal'
import { Alert, Badge, Button, Card, DataTable, PageHeader, Pagination, StatusBadge, TableFooter, VisuallyHidden } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useListado } from '../../../hooks/useListado'
import { planes } from '../../../services/planPlazas'
import { formatearFechaHora } from '../../../utils/fechas'
import { ESTADO_PLAN } from './estados'

const CAMPOS = [
  { name: 'anio_academico', label: 'Año académico', required: true, ancho: 'mitad', hint: 'Formato 2026-2027' },
  { name: 'notas', label: 'Notas', type: 'textarea' },
]

function validar(v) {
  const anio = /^(\d{4})-(\d{4})$/.exec(v.anio_academico)
  return !anio || Number(anio[2]) !== Number(anio[1]) + 1 ? { anio_academico: 'Usa la forma 2026-2027 (dos años consecutivos).' } : {}
}

/** Listado de planes de plazas (RF-032). */
export function PlanesPlazas() {
  const { esGlobal, tienePermiso } = useAuth()
  const listado = useListado(planes)
  const navigate = useNavigate()
  const [nuevo, setNuevo] = useState(false)

  const columnas = [
    {
      key: 'anio_academico',
      header: 'Curso',
      render: (p) => (
        <>
          <strong>{p.anio_academico}</strong> {p.es_complementario && <Badge tone="info">Complementario</Badge>}
        </>
      ),
    },
    { key: 'estado', header: 'Estado', render: (p) => <StatusBadge estado={p.estado} mapa={ESTADO_PLAN} /> },
    { key: 'version', header: 'Versión', align: 'center', render: (p) => p.version || '—' },
    { key: 'lineas', header: 'Carreras', align: 'center', render: (p) => p.totales.lineas },
    { key: 'plazas', header: 'Plazas', align: 'center', render: (p) => (p.estado === 'publicado' ? p.totales.plazas_aprobadas : p.totales.plazas_propuestas) },
    { key: 'aprobacion', header: 'Aprobado', render: (p) => (p.fecha_aprobacion ? `${p.aprobado_por_nombre} · ${formatearFechaHora(p.fecha_aprobacion)}` : '—') },
    {
      key: 'ver',
      header: <VisuallyHidden>Abrir</VisuallyHidden>,
      align: 'right',
      render: (p) => (
        <Button as={Link} to={`/admin/plan-plazas/${p.id}`} variant="ghost" size="sm" icon={Eye} aria-label={`Abrir el plan ${p.anio_academico}`} />
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Plan de Plazas"
        subtitle="Propuesta de la Comisión de Ingreso, revisión de las entidades y aprobación del Vicerrector."
        actions={
          esGlobal &&
          tienePermiso('plan_plazas.crear') && (
            <Button icon={Plus} onClick={() => setNuevo(true)}>
              Nuevo plan
            </Button>
          )
        }
      />
      <Card>
        {listado.error && <Alert tone="danger">{listado.error}</Alert>}
        <DataTable columns={columnas} rows={listado.filas} loading={listado.cargando} emptyMessage="Todavía no hay planes de plazas." />
        <TableFooter>
          <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
        </TableFooter>
      </Card>
      {nuevo && (
        <RecursoModal
          open
          titulo="Nuevo plan de plazas"
          campos={CAMPOS}
          valoresIniciales={{ anio_academico: '', notas: '' }}
          validar={validar}
          onGuardar={(v) => planes.crear(v)}
          onClose={(creado) => (creado ? navigate(`/admin/plan-plazas/${creado.id}`) : setNuevo(false))}
        />
      )}
    </>
  )
}
