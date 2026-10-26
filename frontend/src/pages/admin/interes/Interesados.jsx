import { FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'
import { Alert, Button, Card, DataTable, Input, Pagination, Select, TableFooter, Toolbar, useToast } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useListado } from '../../../hooks/useListado'
import { useOpciones } from '../../../hooks/useOpciones'
import { mensajeDeError } from '../../../services/errores'
import { expresiones } from '../../../services/interes'
import { carreras, cumFum, facultades } from '../../../services/nomencladores'
import { descargarBlob } from '../../../utils/descargar'
import { formatearFechaHora } from '../../../utils/fechas'

const COLUMNAS = [
  { key: 'nombre', header: 'Nombre', render: (e) => <strong>{e.nombre}</strong> },
  { key: 'ci', header: 'CI' },
  { key: 'celular', header: 'Celular' },
  { key: 'email', header: 'Email' },
  { key: 'carrera', header: 'Carrera' },
  { key: 'entidad', header: 'Entidad' },
  { key: 'created_at', header: 'Fecha', render: (e) => formatearFechaHora(e.created_at) },
]

/** Parámetros de la API a partir de los filtros (la entidad combina Facultad y CUM/FUM). */
function parametros({ entidad, ...resto }) {
  const limpios = Object.fromEntries(Object.entries(resto).filter(([, v]) => v !== ''))
  if (!entidad) return limpios
  const [campo, id] = entidad.split(':')
  return { ...limpios, [campo]: id }
}

const recurso = { ruta: expresiones.ruta, listar: (params) => expresiones.listar(parametros(params)) }

/** Interesados en la oferta (RF-031). Contiene datos personales: cada rol ve los de su ámbito. */
export function Interesados({ convocatoria }) {
  const { esGlobal, tienePermiso } = useAuth()
  const toast = useToast()
  const [exportando, setExportando] = useState(false)
  const listado = useListado(recurso, {
    filtrosIniciales: { convocatoria: convocatoria?.id ?? '', carrera: '', entidad: '', buscar: '' },
  })
  const opcionesCarrera = useOpciones(carreras)
  const opcionesFacultad = useOpciones(esGlobal ? facultades : null)
  const opcionesCum = useOpciones(esGlobal ? cumFum : null)
  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  async function exportar() {
    setExportando(true)
    try {
      descargarBlob(await expresiones.exportar(parametros(listado.filtros)), 'interesados.xlsx')
    } catch (error) {
      toast.error(mensajeDeError(error))
    } finally {
      setExportando(false)
    }
  }

  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]

  return (
    <Card>
      <Toolbar>
        <Input label="Buscar" type="search" placeholder="Nombre" {...filtro('buscar')} />
        <Select label="Carrera" placeholder="Todas" options={opcionesCarrera} {...filtro('carrera')} />
        {esGlobal && <Select label="Entidad" placeholder="Todas" options={entidades} {...filtro('entidad')} />}
        {tienePermiso('interes.exportar') && (
          <Button variant="secondary" icon={FileSpreadsheet} loading={exportando} onClick={exportar} disabled={listado.total === 0}>
            Exportar Excel
          </Button>
        )}
      </Toolbar>
      {listado.error && <Alert tone="danger">{listado.error}</Alert>}
      <DataTable columns={COLUMNAS} rows={listado.filas} loading={listado.cargando} emptyMessage="Todavía no hay expresiones de interés." />
      <TableFooter>
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      </TableFooter>
    </Card>
  )
}
