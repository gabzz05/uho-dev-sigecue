import { Megaphone } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { FormularioInteres } from '../../components/landing/FormularioInteres/FormularioInteres'
import { SeccionInstitucional } from '../../components/landing/SeccionInstitucional/SeccionInstitucional'
import { TarjetaCarrera } from '../../components/landing/TarjetaCarrera/TarjetaCarrera'
import { Alert, Button, EmptyState, Input, Pagination, Select, Spinner } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { useCarga } from '../../hooks/useCarga'
import { useListado } from '../../hooks/useListado'
import { publico } from '../../services/publico'
import { formatearFecha } from '../../utils/fechas'
import styles from './Inicio.module.css'

const DURACIONES = [4, 5, 6].map((n) => ({ value: String(n), label: `${n} años` }))
const FILTROS = { buscar: '', entidad: '', municipio: '', duracion: '' }

/** "facultad:3" → { facultad: 3 }. El select combina Facultades y CUM/FUM. */
function aParametros({ entidad, ...resto }) {
  if (!entidad) return resto
  const [campo, id] = entidad.split(':')
  return { ...resto, [campo]: id }
}

/** Adapta un recurso para que acepte el filtro combinado de entidad. */
function conEntidad(recurso) {
  return { ruta: recurso.ruta, listar: (params) => recurso.listar(aParametros(params)) }
}
const ofertaFiltrable = conEntidad(publico.oferta)

function Catalogo({ convocatoria, filtros, onInteres }) {
  // Con convocatoria abierta: la oferta (carrera + entidad). Sin ella: el catálogo de carreras.
  const listado = useListado(convocatoria ? ofertaFiltrable : publico.carreras, { filtrosIniciales: FILTROS, pageSize: 12 })
  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  const entidades = [
    ...filtros.facultades.map((f) => ({ value: `facultad:${f.id}`, label: f.nombre })),
    ...filtros.cum_fum.map((c) => ({ value: `cum_fum:${c.id}`, label: c.nombre })),
  ]

  return (
    <section id="carreras" className={styles.catalogo} aria-labelledby="titulo-carreras">
      <h2 id="titulo-carreras" className={styles.subtitulo}>
        {convocatoria ? `Carreras ofertadas — curso ${convocatoria.anio_academico}` : 'Carreras por encuentro'}
      </h2>
      <div className={styles.filtros}>
        <Input label="Buscar carrera" type="search" placeholder="p. ej. Informática" {...filtro('buscar')} />
        {convocatoria && (
          <>
            <Select label="Facultad / CUM" placeholder="Todas" options={entidades} {...filtro('entidad')} />
            <Select
              label="Municipio"
              placeholder="Todos"
              options={filtros.municipios.map((m) => ({ value: String(m.id), label: m.nombre }))}
              {...filtro('municipio')}
            />
          </>
        )}
        <Select label="Duración" placeholder="Todas" options={DURACIONES} {...filtro('duracion')} />
      </div>

      {listado.error && <Alert tone="danger">{listado.error}</Alert>}
      {listado.cargando && listado.filas.length === 0 ? (
        <Spinner label="Cargando carreras" />
      ) : listado.filas.length === 0 ? (
        <EmptyState title="No hay carreras con estos filtros" message="Prueba con otra búsqueda." />
      ) : (
        <div className={styles.grid} aria-busy={listado.cargando || undefined}>
          {listado.filas.map((fila) =>
            convocatoria ? (
              <TarjetaCarrera key={fila.id} carrera={fila.carrera} entidad={fila.entidad} onInteres={() => onInteres(fila)} />
            ) : (
              <TarjetaCarrera key={fila.id} carrera={fila} />
            ),
          )}
        </div>
      )}
      {listado.total > listado.pageSize && (
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      )}
    </section>
  )
}

/** Landing pública (RF-019 a RF-025). */
export function InicioPublico() {
  const { usuario } = useAuth()
  const convocatoria = useCarga(publico.convocatoriaInteres)
  const filtros = useCarga(useCallback(() => publico.filtros(), []))
  const [interes, setInteres] = useState(null)

  const abierta = convocatoria.datos

  return (
    <>
      {abierta && (
        <div className={styles.banner} role="region" aria-label="Convocatoria de interés abierta">
          <Megaphone aria-hidden="true" />
          <p>
            <strong>Convocatoria de interés abierta</strong> para el curso {abierta.anio_academico} · hasta el{' '}
            {formatearFecha(abierta.fecha_cierre)}.{abierta.mensaje_publico && <> {abierta.mensaje_publico}</>}
          </p>
        </div>
      )}

      <section className={styles.hero}>
        <h1 className={styles.titulo}>Carreras por Encuentro</h1>
        <p className={styles.texto}>
          Estudia en la modalidad que se adapta a tu vida. Consulta la oferta de las Facultades y de los Centros
          Universitarios de tu municipio.
        </p>
        <div className={styles.acciones}>
          <Button as="a" href="#carreras" variant="inverse" size="lg">
            Ver carreras
          </Button>
          {!usuario && (
            <Button as={Link} to="/login" variant="outline" size="lg" className={styles.ghost}>
              Iniciar sesión
            </Button>
          )}
        </div>
      </section>

      {convocatoria.cargando || filtros.cargando ? (
        <div className={styles.catalogo}>
          <Spinner label="Cargando la oferta" />
        </div>
      ) : (
        <Catalogo
          convocatoria={abierta}
          filtros={filtros.datos ?? { facultades: [], cum_fum: [], municipios: [] }}
          onInteres={setInteres}
        />
      )}

      <SeccionInstitucional />

      {interes && <FormularioInteres oferta={interes} convocatoria={abierta} onClose={() => setInteres(null)} />}
    </>
  )
}
