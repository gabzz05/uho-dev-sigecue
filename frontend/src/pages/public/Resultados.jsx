import { Search } from 'lucide-react'
import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  EmptyState,
  Input,
  PageHeader,
  Pagination,
  Select,
  Spinner,
  TableFooter,
  Toolbar,
} from '../../components/ui'
import { useCarga } from '../../hooks/useCarga'
import { useListado } from '../../hooks/useListado'
import { mensajeDeError } from '../../services/errores'
import { publico } from '../../services/publico'
import styles from './Resultados.module.css'

const COLUMNAS = [
  { key: 'nombre', header: 'Nombre y apellidos', render: (r) => <strong>{r.nombre}</strong> },
  { key: 'ci', header: 'CI' },
  { key: 'carrera', header: 'Carrera' },
  { key: 'entidad', header: 'Entidad' },
  { key: 'convocatoria', header: 'Convocatoria' },
]

const comoOpciones = (lista) => lista.map((valor) => ({ value: valor, label: valor }))

/** Resultados del otorgamiento (RF-063): listado de otorgados y consulta del resultado propio. Solo visualización. */
export function Resultados() {
  const filtros = useCarga(publico.filtrosResultados)

  return (
    <div className={styles.page}>
      <PageHeader
        title="Resultados del otorgamiento"
        subtitle="Aspirantes que obtuvieron plaza en las carreras por encuentro. El CI se muestra parcialmente para proteger los datos personales."
      />
      <div className={styles.pila}>
        <ConsultaIndividual />
        {filtros.cargando ? (
          <Spinner label="Cargando resultados" />
        ) : filtros.error ? (
          <Alert tone="danger">{filtros.error}</Alert>
        ) : filtros.datos.convocatorias.length === 0 ? (
          <EmptyState title="No hay resultados publicados" message="Los resultados aparecen aquí cuando se publica el otorgamiento de una convocatoria." />
        ) : (
          <Listado filtros={filtros.datos} />
        )}
      </div>
    </div>
  )
}

function ConsultaIndividual() {
  const [ci, setCi] = useState('')
  const [estado, setEstado] = useState({ cargando: false, resultados: null, error: '' })

  async function consultar(evento) {
    evento.preventDefault()
    if (!/^\d{11}$/.test(ci)) {
      setEstado({ cargando: false, resultados: null, error: 'Escribe los 11 dígitos de tu carnet de identidad.' })
      return
    }
    setEstado({ cargando: true, resultados: null, error: '' })
    try {
      const { resultados } = await publico.consultarResultado(ci)
      setEstado({ cargando: false, resultados, error: '' })
    } catch (error) {
      setEstado({ cargando: false, resultados: null, error: mensajeDeError(error) })
    }
  }

  return (
    <Card>
      <CardHeader title="Consulta tu resultado" />
      <CardBody>
        <form className={styles.consulta} onSubmit={consultar} noValidate>
          <Input
            label="Carnet de identidad"
            inputMode="numeric"
            maxLength={11}
            autoComplete="off"
            value={ci}
            onChange={(e) => setCi(e.target.value.replace(/\D/g, ''))}
          />
          <Button type="submit" icon={Search} loading={estado.cargando}>
            Consultar
          </Button>
        </form>
        {estado.error && (
          <Alert tone="info" className={styles.respuesta}>
            {estado.error}
          </Alert>
        )}
        {estado.resultados && (
          <ul className={styles.respuesta} aria-live="polite">
            {estado.resultados.map((r) => (
              <li key={r.convocatoria}>
                <Alert tone={r.resultado === 'Otorgado' ? 'success' : 'info'} title={`${r.convocatoria}: ${r.resultado}`}>
                  {r.carrera ? `${r.carrera} — ${r.entidad}` : 'No obtuviste plaza en esta convocatoria.'}
                </Alert>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

function Listado({ filtros }) {
  const listado = useListado(publico.resultados, {
    filtrosIniciales: { otorgamiento: String(filtros.convocatorias.at(-1).id), carrera: '', entidad: '' },
    pageSize: 50,
  })
  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  return (
    <Card>
      <Toolbar>
        {/* Cada convocatoria es un listado aparte: no se mezclan la primera y la segunda. */}
        <Select label="Convocatoria" options={filtros.convocatorias.map((c) => ({ value: String(c.id), label: c.nombre }))} {...filtro('otorgamiento')} />
        <Select label="Carrera" placeholder="Todas" options={comoOpciones(filtros.carreras)} {...filtro('carrera')} />
        <Select label="Entidad" placeholder="Todas" options={comoOpciones(filtros.entidades)} {...filtro('entidad')} />
      </Toolbar>
      {listado.error && <Alert tone="danger">{listado.error}</Alert>}
      <DataTable
        columns={COLUMNAS}
        rows={listado.filas}
        rowKey={(r) => `${r.ci}-${r.carrera}-${r.entidad}`}
        loading={listado.cargando}
        caption="Otorgados por carrera, entidad y apellidos"
        emptyMessage="No hay otorgados con esos filtros."
      />
      <TableFooter>
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      </TableFooter>
    </Card>
  )
}
