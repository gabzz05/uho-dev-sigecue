import { CalendarDays, FileSpreadsheet, FileText } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  Input,
  PageHeader,
  Pagination,
  Select,
  Spinner,
  StatusBadge,
  TableFooter,
  Toolbar,
  useToast,
} from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useCarga } from '../../../hooks/useCarga'
import { useFormulario } from '../../../hooks/useFormulario'
import { useListado } from '../../../hooks/useListado'
import { mensajeDeError } from '../../../services/errores'
import { otorgamientos } from '../../../services/otorgamiento'
import { prematriculasAdmin } from '../../../services/prematricula'
import { descargarBlob } from '../../../utils/descargar'
import { ESTADOS_PREMATRICULA } from '../../../utils/estadosPrematricula'
import { formatearFecha, formatearFechaHora } from '../../../utils/fechas'
import styles from './Prematricula.module.css'

const ESTADOS = Object.entries(ESTADOS_PREMATRICULA).map(([value, { label }]) => ({ value, label }))
const etiqueta = (c) => `${c.numero}.ª convocatoria ${c.anio_academico}`

const COLUMNAS = [
  {
    key: 'aspirante_nombre',
    header: 'Aspirante',
    render: (p) => (
      <Link to={`/admin/prematricula/${p.id}`} className={styles.enlace}>
        {p.aspirante_nombre}
      </Link>
    ),
  },
  { key: 'carrera', header: 'Carrera', render: (p) => `${p.carrera} — ${p.entidad}` },
  { key: 'estado', header: 'Estado', render: (p) => <StatusBadge estado={p.estado} mapa={ESTADOS_PREMATRICULA} /> },
  { key: 'faltantes', header: 'Falta', render: (p) => (p.faltantes.length ? p.faltantes.join(', ') : '—') },
  { key: 'fecha_aprobacion', header: 'Aprobada', render: (p) => (p.fecha_aprobacion ? `${formatearFechaHora(p.fecha_aprobacion)} · ${p.aprobado_por}` : '—') },
]

const cargar = () => Promise.all([otorgamientos.listar(), prematriculasAdmin.periodos(), prematriculasAdmin.opcionesFaltantes()])

/** Panel de prematrícula (RF-068 a RF-072): período, expedientes, faltantes y exportación. */
export function Prematriculas() {
  const carga = useCarga(cargar)
  const [periodosNuevos, setPeriodosNuevos] = useState([])
  const [elegido, setElegido] = useState('')

  if (carga.cargando) return <Spinner label="Cargando la prematrícula" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const [lista, periodosIniciales, faltantes] = carga.datos
  const publicados = lista.filter((o) => o.estado === 'publicado')
  const periodos = [...periodosNuevos, ...periodosIniciales.filter((p) => !periodosNuevos.some((n) => n.id === p.id))]
  const actual = publicados.find((o) => String(o.id) === elegido) ?? publicados[0]

  return (
    <>
      <PageHeader title="Prematrícula" subtitle="Expedientes de los aspirantes otorgados: documentos, revisión y aprobación." />
      {publicados.length === 0 ? (
        <Alert tone="info">La prematrícula empieza cuando se publica un otorgamiento.</Alert>
      ) : (
        <div className={styles.pila}>
          {publicados.length > 1 && (
            <div className={styles.selector}>
              <Select
                label="Convocatoria"
                options={publicados.map((o) => ({ value: String(o.id), label: etiqueta(o.convocatoria) }))}
                value={String(actual.id)}
                onChange={(e) => setElegido(e.target.value)}
              />
            </div>
          )}
          <Periodo
            key={`periodo-${actual.id}`}
            otorgamiento={actual}
            periodo={periodos.find((p) => p.otorgamiento === actual.id)}
            onGuardado={(p) => setPeriodosNuevos((n) => [p, ...n.filter((x) => x.id !== p.id)])}
          />
          <Listado key={`listado-${actual.id}`} otorgamiento={actual} faltantes={faltantes} />
        </div>
      )}
    </>
  )
}

function Periodo({ otorgamiento, periodo, onGuardado }) {
  const { tienePermiso } = useAuth()
  const toast = useToast()
  const puedeConfigurar = tienePermiso('prematricula.configurar') && !periodo?.cerrado
  const formulario = useFormulario({ fecha_inicio: periodo?.fecha_inicio ?? '', fecha_cierre: periodo?.fecha_cierre ?? '' })

  async function guardar(evento) {
    evento.preventDefault()
    const datos = await formulario.enviar(
      (v) => prematriculasAdmin.configurarPeriodo({ otorgamiento: otorgamiento.id, ...v }),
      ({ fecha_inicio: inicio, fecha_cierre: cierre }) => {
        if (!inicio || !cierre) return { fecha_cierre: 'Indica las dos fechas.' }
        return cierre < inicio ? { fecha_cierre: 'No puede ser anterior al inicio.' } : {}
      },
    )
    if (datos) {
      onGuardado(datos)
      toast.exito(periodo ? 'Se actualizó el período.' : 'Se abrió la prematrícula y se avisó a los otorgados.')
    }
  }

  return (
    <Card>
      <CardHeader title="Período de prematrícula" />
      <CardBody>
        {periodo ? (
          <p className={styles.apagado}>
            Del {formatearFecha(periodo.fecha_inicio)} al {formatearFecha(periodo.fecha_cierre)}
            {periodo.abierto ? ' · abierto' : periodo.cerrado ? ' · cerrado' : ' · todavía no empezó'}. El listado público de resultados se ve
            hasta el cierre.
          </p>
        ) : (
          <p className={styles.apagado}>Todavía no se fijó el período. Al fijarlo se crea el expediente de cada otorgado y se le avisa.</p>
        )}
        {puedeConfigurar && (
          <form className={styles.fechas} onSubmit={guardar} noValidate>
            {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
            <Input label="Fecha de inicio" type="date" {...formulario.campo('fecha_inicio')} />
            <Input label="Fecha de cierre" type="date" {...formulario.campo('fecha_cierre')} />
            <Button type="submit" icon={CalendarDays} loading={formulario.enviando}>
              {periodo ? 'Guardar fechas' : 'Abrir prematrícula'}
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  )
}

function parametros({ falta, ...resto }) {
  const limpios = Object.fromEntries(Object.entries(resto).filter(([, v]) => v !== ''))
  if (!falta) return limpios
  const [parametro, id] = falta.split(':')
  return { ...limpios, [parametro]: id }
}

function Listado({ otorgamiento, faltantes }) {
  const { tienePermiso } = useAuth()
  const toast = useToast()
  const [exportando, setExportando] = useState(null)
  const recurso = useMemo(
    () => ({ ruta: `${prematriculasAdmin.ruta}?o=${otorgamiento.id}`, listar: (p) => prematriculasAdmin.listar(parametros({ ...p, otorgamiento: otorgamiento.id })) }),
    [otorgamiento.id],
  )
  const listado = useListado(recurso, { filtrosIniciales: { buscar: '', estado: '', falta: '' }, pageSize: 50 })
  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  const exportar = useCallback(
    async (formato) => {
      setExportando(formato)
      try {
        const params = parametros({ ...listado.filtros, otorgamiento: otorgamiento.id })
        const archivo = formato === 'pdf' ? await prematriculasAdmin.exportarPdf(params) : await prematriculasAdmin.exportarExcel(params)
        descargarBlob(archivo, `prematriculas.${formato === 'pdf' ? 'pdf' : 'xlsx'}`)
      } catch (e) {
        toast.error(mensajeDeError(e))
      } finally {
        setExportando(null)
      }
    },
    [listado.filtros, otorgamiento.id, toast],
  )

  return (
    <Card>
      <Toolbar>
        <Input label="Buscar" type="search" placeholder="Nombre" {...filtro('buscar')} />
        <Select label="Estado" placeholder="Todos" options={ESTADOS} {...filtro('estado')} />
        <Select
          label="Le falta"
          placeholder="Cualquiera"
          options={faltantes.map((f) => ({ value: `${f.parametro}:${f.id}`, label: f.nombre }))}
          {...filtro('falta')}
        />
        {tienePermiso('prematricula.exportar') && (
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
      <DataTable columns={COLUMNAS} rows={listado.filas} loading={listado.cargando} emptyMessage="No hay expedientes con esos filtros." />
      <TableFooter>
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      </TableFooter>
    </Card>
  )
}
