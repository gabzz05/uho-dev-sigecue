import { Lock, PlayCircle } from 'lucide-react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { Badge, BotonConfirmado, CheckboxGroup, useToast } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { convocatoriasSolicitud } from '../../../services/convocatorias'
import { mensajeDeError } from '../../../services/errores'
import { cumFum, facultades } from '../../../services/nomencladores'
import { formatearFecha } from '../../../utils/fechas'

const TONO_ESTADO = { borrador: 'neutral', abierta: 'success', cerrada: 'warning' }
const INICIALES = { anio_academico: '', fecha_inicio: '', fecha_cierre: '', mensaje_publico: '', entidades: [] }

const COLUMNAS = [
  {
    key: 'anio_academico',
    header: 'Convocatoria',
    render: (c) => (
      <>
        <strong>{c.anio_academico}</strong> · {c.numero}.ª
      </>
    ),
  },
  { key: 'periodo', header: 'Período', render: (c) => `${formatearFecha(c.fecha_inicio)} – ${formatearFecha(c.fecha_cierre)}` },
  { key: 'estado', header: 'Estado', render: (c) => <Badge tone={TONO_ESTADO[c.estado]}>{c.estado_nombre}</Badge> },
  { key: 'entidades', header: 'Entidades', render: (c) => (c.entidades.length ? c.entidades.join(', ') : 'Todas las que tienen plazas') },
  { key: 'total_ofertas', header: 'Carreras', align: 'center' },
  { key: 'interesados_notificados', header: 'Interesados avisados', align: 'center', render: (c) => c.interesados_notificados ?? '—' },
]

function validar(v) {
  const errores = {}
  const anio = /^(\d{4})-(\d{4})$/.exec(v.anio_academico)
  if (!anio || Number(anio[2]) !== Number(anio[1]) + 1) errores.anio_academico = 'Usa la forma 2026-2027 (dos años consecutivos).'
  if (!v.fecha_inicio) errores.fecha_inicio = 'Indica la fecha de inicio.'
  if (!v.fecha_cierre) errores.fecha_cierre = 'Indica la fecha de cierre.'
  if (v.fecha_inicio && v.fecha_cierre && v.fecha_cierre < v.fecha_inicio) errores.fecha_cierre = 'No puede ser anterior al inicio.'
  return errores
}

/** Separa "facultad:3" / "cum_fum:5" en las dos listas que espera la API. */
function datos({ anio_academico, fecha_inicio, fecha_cierre, mensaje_publico, entidades }) {
  const de = (tipo) => entidades.filter((e) => e.startsWith(`${tipo}:`)).map((e) => Number(e.split(':')[1]))
  return { anio_academico, fecha_inicio, fecha_cierre, mensaje_publico, facultades: de('facultad'), cum_fums: de('cum_fum') }
}

/** Convocatorias de solicitud de matrícula (RF-040 a RF-043). Las gestionan los roles globales. */
export function Convocatorias() {
  const { esGlobal, tienePermiso } = useAuth()
  const toast = useToast()
  const opcionesFacultad = useOpciones(facultades)
  const opcionesCum = useOpciones(cumFum)
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]
  const puedeGestionar = esGlobal && tienePermiso('convocatorias.editar')

  const campos = (v) => [
    { name: 'anio_academico', label: 'Año académico', required: true, ancho: 'mitad', hint: 'Formato 2026-2027', disabled: Boolean(v.id) },
    { name: 'fecha_inicio', label: 'Fecha de inicio', type: 'date', required: true, ancho: 'mitad' },
    { name: 'fecha_cierre', label: 'Fecha de cierre', type: 'date', required: true, ancho: 'mitad', hint: 'Se cierra sola al terminar este día.' },
    { name: 'mensaje_publico', label: 'Mensaje público', type: 'textarea', hint: 'Se muestra en el aviso de la landing.' },
    {
      name: 'entidades',
      type: 'custom',
      render: (props) => (
        <CheckboxGroup
          legend="Entidades"
          hint={v.estado === 'abierta' ? 'No se cambian con la convocatoria abierta.' : 'Sin marcar ninguna, aplica a todas las entidades con plazas en el plan.'}
          options={entidades}
          {...props}
        />
      ),
    },
  ]

  async function ejecutar(accion, c, mensaje, recargar) {
    try {
      await accion(c.id)
      toast.exito(mensaje)
      recargar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  return (
    <CrudPage
      titulo="Convocatorias de solicitud"
      subtitulo="Período oficial en el que los aspirantes solicitan matrícula. Requiere el plan de plazas publicado del año."
      singular="convocatoria"
      nombreDe={(c) => `la convocatoria ${c.numero}.ª ${c.anio_academico}`}
      recurso={convocatoriasSolicitud}
      columnas={COLUMNAS}
      campos={campos}
      valoresIniciales={INICIALES}
      validar={validar}
      aFormulario={(c) => ({
        ...INICIALES,
        ...c,
        entidades: [...c.facultades.map((id) => `facultad:${id}`), ...c.cum_fums.map((id) => `cum_fum:${id}`)],
      })}
      aDatos={(v) => {
        const d = datos(v)
        // Con la convocatoria abierta, las entidades no se envían (la API no permite cambiarlas).
        if (v.estado === 'abierta') {
          delete d.facultades
          delete d.cum_fums
        }
        return d
      }}
      estado={null}
      placeholderBusqueda="Curso"
      puedeEditarItem={(c) => c.estado !== 'cerrada'}
      puedeEliminarItem={(c) => c.estado === 'borrador'}
      accionesExtra={(c, recargar) =>
        puedeGestionar &&
        (c.estado === 'borrador' ? (
          <BotonConfirmado
            variant="ghost"
            size="sm"
            icon={PlayCircle}
            aria-label={`Abrir la convocatoria ${c.numero}.ª ${c.anio_academico}`}
            titulo="Abrir convocatoria"
            mensaje={
              c.numero === 1
                ? 'Los aspirantes podrán solicitar matrícula y se avisará por correo a quienes expresaron interés este año.'
                : 'Los aspirantes podrán solicitar matrícula en las plazas restantes.'
            }
            onConfirm={() => ejecutar(convocatoriasSolicitud.abrir, c, 'Se abrió la convocatoria.', recargar)}
          />
        ) : c.estado === 'abierta' ? (
          <BotonConfirmado
            variant="ghost"
            size="sm"
            icon={Lock}
            aria-label={`Cerrar la convocatoria ${c.numero}.ª ${c.anio_academico}`}
            titulo="Cerrar convocatoria"
            tone="danger"
            mensaje="Ya no se aceptarán nuevas solicitudes. No se puede deshacer."
            onConfirm={() => ejecutar(convocatoriasSolicitud.cerrar, c, 'Se cerró la convocatoria.', recargar)}
          />
        ) : null)
      }
      permisos={{ crear: puedeGestionar, editar: puedeGestionar, eliminar: puedeGestionar && tienePermiso('convocatorias.eliminar') }}
    />
  )
}
