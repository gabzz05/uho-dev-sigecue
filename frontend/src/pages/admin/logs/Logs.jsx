import { Eye } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Alert, Badge, Button, Card, DataTable, Input, Modal, PageHeader, Pagination, Select, TableFooter, Toolbar } from '../../../components/ui'
import { useCarga } from '../../../hooks/useCarga'
import { useListado } from '../../../hooks/useListado'
import { logs } from '../../../services/auditoria'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Logs.module.css'

const RESULTADOS = [
  { value: 'exito', label: 'Éxito' },
  { value: 'error', label: 'Error' },
]
const FILTROS = { usuario_nombre: '', accion: '', modulo: '', resultado: '', desde: '', hasta: '' }

const insignia = (log) => <Badge tone={log.resultado === 'exito' ? 'success' : 'danger'}>{log.resultado === 'exito' ? 'Éxito' : 'Error'}</Badge>

function Detalle({ log, onClose }) {
  const filas = [
    ['Fecha y hora', formatearFechaHora(log.created_at)],
    ['Usuario', log.usuario_nombre || 'Anónimo'],
    ['Acción', log.accion],
    ['Módulo', log.modulo],
    ['Entidad afectada', [log.entidad_afectada, log.entidad_id].filter(Boolean).join(' #') || '—'],
    ['Método y ruta', `${log.metodo} ${log.ruta}`.trim() || '—'],
    ['Dirección IP', log.ip ?? '—'],
    ['Resultado', insignia(log)],
    ['Código HTTP', log.codigo_http ?? '—'],
  ]
  const hayDetalle = log.detalle && Object.keys(log.detalle).length > 0

  return (
    <Modal open onClose={onClose} title="Registro de auditoría" size="lg">
      <dl className={styles.detalle}>
        {filas.map(([etiqueta, valor]) => (
          <div key={etiqueta} className={styles.fila}>
            <dt>{etiqueta}</dt>
            <dd>{valor}</dd>
          </div>
        ))}
      </dl>
      {hayDetalle && <pre className={styles.json}>{JSON.stringify(log.detalle, null, 2)}</pre>}
    </Modal>
  )
}

/** Consulta de los logs de auditoría (RG-010). Solo lectura: los registros no se modifican. */
export function Logs() {
  const listado = useListado(logs, { filtrosIniciales: FILTROS })
  const modulos = useCarga(useCallback(() => logs.modulos(), []))
  const [seleccionado, setSeleccionado] = useState(null)

  const filtro = (nombre) => ({
    value: listado.filtros[nombre],
    onChange: (e) => listado.cambiarFiltro(nombre, e.target.value),
  })

  const columnas = [
    { key: 'created_at', header: 'Fecha y hora', render: (l) => <span className={styles.nowrap}>{formatearFechaHora(l.created_at)}</span> },
    { key: 'usuario_nombre', header: 'Usuario', render: (l) => l.usuario_nombre || <em>Anónimo</em> },
    { key: 'accion', header: 'Acción', render: (l) => <code className={styles.accion}>{l.accion}</code> },
    { key: 'modulo', header: 'Módulo' },
    { key: 'ip', header: 'IP', render: (l) => l.ip ?? '—' },
    { key: 'resultado', header: 'Resultado', render: insignia },
    {
      key: 'ver',
      header: <span className={styles.srOnly}>Detalle</span>,
      align: 'right',
      render: (l) => (
        <Button variant="ghost" size="sm" icon={Eye} aria-label={`Ver detalle del registro ${l.id}`} onClick={() => setSeleccionado(l)} />
      ),
    },
  ]

  return (
    <>
      <PageHeader title="Logs de auditoría" subtitle="Acciones de los usuarios: quién, qué, cuándo, desde dónde y con qué resultado." />
      <Card>
        <Toolbar>
          <Input label="Usuario" type="search" placeholder="Nombre de usuario" {...filtro('usuario_nombre')} />
          <Input label="Acción" type="search" placeholder="p. ej. POST" {...filtro('accion')} />
          <Select
            label="Módulo"
            placeholder="Todos"
            options={(modulos.datos ?? []).map((m) => ({ value: m, label: m }))}
            {...filtro('modulo')}
          />
          <Select label="Resultado" placeholder="Todos" options={RESULTADOS} {...filtro('resultado')} />
          <Input label="Desde" type="date" {...filtro('desde')} />
          <Input label="Hasta" type="date" min={listado.filtros.desde || undefined} {...filtro('hasta')} />
        </Toolbar>
        {listado.error && <Alert tone="danger">{listado.error}</Alert>}
        <DataTable
          columns={columnas}
          rows={listado.filas}
          loading={listado.cargando}
          emptyMessage="No hay registros con estos filtros."
        />
        <TableFooter>
          <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
        </TableFooter>
      </Card>
      {seleccionado && <Detalle log={seleccionado} onClose={() => setSeleccionado(null)} />}
    </>
  )
}
