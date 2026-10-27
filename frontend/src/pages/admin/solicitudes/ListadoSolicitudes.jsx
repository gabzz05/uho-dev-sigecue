import { FileSpreadsheet, FileText } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  DataTable,
  Input,
  Pagination,
  Select,
  StatusBadge,
  TableFooter,
  Toolbar,
  useToast,
} from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useListado } from '../../../hooks/useListado'
import { useOpciones } from '../../../hooks/useOpciones'
import { mensajeDeError } from '../../../services/errores'
import { cumFum, facultades } from '../../../services/nomencladores'
import { publico } from '../../../services/publico'
import { solicitudesAdmin } from '../../../services/solicitudes'
import { descargarBlob } from '../../../utils/descargar'
import { ESTADOS_SOLICITUD, textoIndice } from '../../../utils/estadosSolicitud'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Solicitudes.module.css'

const ESTADOS = Object.entries(ESTADOS_SOLICITUD)
  .filter(([valor]) => valor !== 'borrador')
  .map(([value, { label }]) => ({ value, label }))

const COLUMNAS = [
  {
    key: 'nombre',
    header: 'Aspirante',
    render: (s) => (
      <Link to={`/admin/solicitudes/${s.id}`} className={styles.enlace}>
        {s.nombre}
      </Link>
    ),
  },
  { key: 'ci', header: 'CI' },
  { key: 'indice', header: 'Índice', render: textoIndice },
  {
    key: 'carreras',
    header: 'Carreras',
    render: (s) => (
      <ul className={styles.listaCompacta}>
        {s.carreras.map((c) => (
          <li key={c.oferta.id}>
            {c.prioridad}. {c.oferta.carrera_nombre} <span className={styles.apagado}>— {c.oferta.entidad_nombre}</span>
          </li>
        ))}
      </ul>
    ),
  },
  {
    key: 'estado',
    header: 'Estado',
    render: (s) => (
      <span className={styles.estado}>
        <StatusBadge estado={s.estado} mapa={ESTADOS_SOLICITUD} />
        {s.observaciones_sin_resolver > 0 && <Badge tone="warning">{s.observaciones_sin_resolver} obs.</Badge>}
      </span>
    ),
  },
  { key: 'confirmada_at', header: 'Confirmada', render: (s) => formatearFechaHora(s.confirmada_at) },
]

/** Parámetros de la API: la entidad combina Facultad y CUM/FUM; los vacíos no se envían. */
function parametros({ entidad, con_observaciones, ...resto }) {
  const limpios = Object.fromEntries(Object.entries(resto).filter(([, v]) => v !== '' && v != null))
  if (con_observaciones) limpios.con_observaciones = 'true'
  if (!entidad) return limpios
  const [campo, id] = entidad.split(':')
  return { ...limpios, [campo]: id }
}

/** Listado de solicitudes con los filtros de RF-052 y la exportación de RF-056. */
export function ListadoSolicitudes({ convocatoria }) {
  const { esGlobal, tienePermiso } = useAuth()
  const toast = useToast()
  const [exportando, setExportando] = useState(null)
  // La convocatoria va en el recurso: al cambiarla se recarga el listado.
  const recurso = useMemo(
    () => ({ ruta: `${solicitudesAdmin.ruta}?c=${convocatoria}`, listar: (p) => solicitudesAdmin.listar(parametros({ ...p, convocatoria })) }),
    [convocatoria],
  )
  const listado = useListado(recurso, {
    filtrosIniciales: { buscar: '', estado: '', carrera: '', entidad: '', desde: '', hasta: '', indice_min: '', indice_max: '', con_observaciones: false },
  })
  // El catálogo público de carreras: los roles locales no siempre tienen permiso sobre los nomencladores.
  const opcionesCarrera = useOpciones(publico.carreras)
  const opcionesFacultad = useOpciones(esGlobal ? facultades : null)
  const opcionesCum = useOpciones(esGlobal ? cumFum : null)
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]
  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  async function exportar(formato) {
    setExportando(formato)
    try {
      const params = parametros({ ...listado.filtros, convocatoria })
      const archivo = formato === 'pdf' ? await solicitudesAdmin.exportarPdf(params) : await solicitudesAdmin.exportarExcel(params)
      descargarBlob(archivo, formato === 'pdf' ? 'solicitudes.pdf' : 'solicitudes.xlsx')
    } catch (error) {
      toast.error(mensajeDeError(error))
    } finally {
      setExportando(null)
    }
  }

  return (
    <Card>
      <Toolbar>
        <Input label="Buscar" type="search" placeholder="Nombre o CI completo" {...filtro('buscar')} />
        <Select label="Estado" placeholder="Todos" options={ESTADOS} {...filtro('estado')} />
        <Select label="Carrera" placeholder="Todas" options={opcionesCarrera} {...filtro('carrera')} />
        {esGlobal && <Select label="Entidad" placeholder="Todas" options={entidades} {...filtro('entidad')} />}
      </Toolbar>
      <Toolbar>
        <Input label="Confirmada desde" type="date" {...filtro('desde')} />
        <Input label="Hasta" type="date" {...filtro('hasta')} />
        <Input label="Índice mínimo" type="number" min={0} max={100} step={0.01} {...filtro('indice_min')} />
        <Input label="Índice máximo" type="number" min={0} max={100} step={0.01} {...filtro('indice_max')} />
        <Checkbox
          label="Con observaciones sin resolver"
          checked={listado.filtros.con_observaciones}
          onChange={(e) => listado.cambiarFiltro('con_observaciones', e.target.checked)}
        />
        {tienePermiso('solicitudes.exportar') && (
          <div className={styles.exportar}>
            <Button variant="secondary" icon={FileSpreadsheet} loading={exportando === 'excel'} onClick={() => exportar('excel')} disabled={listado.total === 0}>
              Excel
            </Button>
            <Button variant="secondary" icon={FileText} loading={exportando === 'pdf'} onClick={() => exportar('pdf')} disabled={listado.total === 0}>
              PDF
            </Button>
          </div>
        )}
      </Toolbar>
      {listado.error && <Alert tone="danger">{listado.error}</Alert>}
      <DataTable columns={COLUMNAS} rows={listado.filas} loading={listado.cargando} emptyMessage="No hay solicitudes con esos filtros." />
      <TableFooter>
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      </TableFooter>
    </Card>
  )
}
