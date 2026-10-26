import { CrudPage } from '../../../components/crud/CrudPage'
import { Alert, Badge } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { ofertas } from '../../../services/interes'
import { carreras, cumFum, facultades } from '../../../services/nomencladores'

const COLUMNAS = [
  { key: 'carrera_nombre', header: 'Carrera', render: (o) => <strong>{o.carrera_nombre}</strong> },
  { key: 'entidad', header: 'Entidad', render: (o) => o.entidad.nombre },
  { key: 'municipio', header: 'Municipio', render: (o) => o.entidad.municipio },
  {
    key: 'asignada_por_ci',
    header: 'Origen',
    render: (o) => <Badge tone={o.asignada_por_ci ? 'primary' : 'neutral'}>{o.asignada_por_ci ? 'Comisión de Ingreso' : 'Entidad'}</Badge>,
  },
  { key: 'total_interesados', header: 'Interesados', align: 'center' },
]

function datos(convocatoria) {
  return ({ carrera, entidad }) => {
    const base = { convocatoria: convocatoria.id, carrera }
    if (!entidad) return base
    const [campo, id] = entidad.split(':')
    return { ...base, [campo]: id }
  }
}

/** Oferta de carreras de una convocatoria (RF-027, RF-028). */
export function Oferta({ convocatoria }) {
  const { esGlobal, tienePermiso, usuario } = useAuth()
  const opcionesCarrera = useOpciones(carreras)
  const opcionesFacultad = useOpciones(esGlobal ? facultades : null)
  const opcionesCum = useOpciones(esGlobal ? cumFum : null)

  if (!convocatoria) return <Alert tone="info">Crea una convocatoria de interés para definir su oferta.</Alert>

  const editable = convocatoria.estado !== 'cerrada'
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]
  // La CI asigna a cualquier entidad; un rol local agrega a la suya sin elegirla.
  const campos = [
    { name: 'carrera', label: 'Carrera del catálogo', type: 'select', options: opcionesCarrera, required: true },
    ...(esGlobal ? [{ name: 'entidad', label: 'Facultad o CUM/FUM', type: 'select', options: entidades, required: true }] : []),
  ]

  return (
    <>
      {!editable && <Alert tone="warning">La convocatoria está cerrada: su oferta ya no se puede modificar.</Alert>}
      {editable && !esGlobal && (
        <Alert tone="info">
          Agrega carreras del catálogo a la oferta de {usuario.entidad?.nombre ?? 'tu entidad'}. Las asignadas por la Comisión de Ingreso no se
          pueden quitar.
        </Alert>
      )}
      <CrudPage
        key={convocatoria.id}
        conEncabezado={false}
        singular="carrera de la oferta"
        etiquetaNuevo="Agregar carrera"
        nombreDe={(o) => o.carrera_nombre ?? 'la carrera'}
        recurso={ofertas}
        filtrosFijos={{ convocatoria: convocatoria.id }}
        columnas={COLUMNAS}
        campos={campos}
        valoresIniciales={{ carrera: '', entidad: '' }}
        validar={(v) => ({
          ...(!v.carrera ? { carrera: 'Selecciona la carrera.' } : {}),
          ...(esGlobal && !v.entidad ? { entidad: 'Selecciona la entidad.' } : {}),
        })}
        aDatos={datos(convocatoria)}
        estado={null}
        placeholderBusqueda="Carrera"
        puedeEliminarItem={(o) => esGlobal || !o.asignada_por_ci}
        permisos={{ crear: editable && tienePermiso('interes.crear'), eliminar: editable && tienePermiso('interes.editar') }}
      />
    </>
  )
}
