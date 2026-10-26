import { Lock, PlayCircle } from 'lucide-react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { Badge, BotonConfirmado, useToast } from '../../../components/ui'
import { mensajeDeError } from '../../../services/errores'
import { convocatoriasInteres } from '../../../services/interes'
import { formatearFecha } from '../../../utils/fechas'

const ESTADOS_CONVOCATORIA = {
  borrador: { label: 'Borrador', tone: 'neutral' },
  abierta: { label: 'Abierta', tone: 'success' },
  cerrada: { label: 'Cerrada', tone: 'warning' },
}

const INICIALES = { anio_academico: '', fecha_inicio: '', fecha_cierre: '', mensaje_publico: '' }

const CAMPOS = (v) => [
  {
    name: 'anio_academico',
    label: 'Año académico',
    required: true,
    ancho: 'mitad',
    hint: 'Formato 2026-2027',
    disabled: Boolean(v.id) && v.estado !== 'borrador',
  },
  { name: 'fecha_inicio', label: 'Fecha de inicio', type: 'date', required: true, ancho: 'mitad' },
  { name: 'fecha_cierre', label: 'Fecha de cierre', type: 'date', required: true, ancho: 'mitad', hint: 'Se cierra sola al terminar este día.' },
  { name: 'mensaje_publico', label: 'Mensaje público', type: 'textarea', hint: 'Se muestra en el aviso de la landing.' },
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

const COLUMNAS = [
  { key: 'anio_academico', header: 'Curso', render: (c) => <strong>{c.anio_academico}</strong> },
  { key: 'fechas', header: 'Período', render: (c) => `${formatearFecha(c.fecha_inicio)} – ${formatearFecha(c.fecha_cierre)}` },
  { key: 'estado', header: 'Estado', render: (c) => <Badge tone={ESTADOS_CONVOCATORIA[c.estado].tone}>{c.estado_nombre}</Badge> },
  { key: 'total_ofertas', header: 'Carreras', align: 'center' },
  { key: 'total_interesados', header: 'Interesados', align: 'center' },
]

/** Convocatorias de interés (RF-026). Las gestiona la Comisión de Ingreso. */
export function Convocatorias({ puedeGestionar }) {
  const toast = useToast()

  async function ejecutar(accion, item, mensaje, recargar) {
    try {
      await accion(item.id)
      toast.exito(mensaje)
      recargar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  return (
    <CrudPage
      conEncabezado={false}
      singular="convocatoria"
      nombreDe={(c) => `la convocatoria ${c.anio_academico}`}
      recurso={convocatoriasInteres}
      columnas={COLUMNAS}
      campos={CAMPOS}
      valoresIniciales={INICIALES}
      validar={validar}
      aFormulario={(c) => ({ ...INICIALES, ...c })}
      aDatos={({ anio_academico, fecha_inicio, fecha_cierre, mensaje_publico }) => ({ anio_academico, fecha_inicio, fecha_cierre, mensaje_publico })}
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
            aria-label={`Abrir la convocatoria ${c.anio_academico}`}
            titulo="Abrir convocatoria"
            mensaje={`La landing empezará a aceptar expresiones de interés para el curso ${c.anio_academico}.`}
            onConfirm={() => ejecutar(convocatoriasInteres.abrir, c, `Se abrió la convocatoria ${c.anio_academico}.`, recargar)}
          />
        ) : c.estado === 'abierta' ? (
          <BotonConfirmado
            variant="ghost"
            size="sm"
            icon={Lock}
            aria-label={`Cerrar la convocatoria ${c.anio_academico}`}
            titulo="Cerrar convocatoria"
            tone="danger"
            mensaje="Ya no se aceptarán expresiones de interés y la oferta quedará bloqueada. No se puede deshacer."
            onConfirm={() => ejecutar(convocatoriasInteres.cerrar, c, `Se cerró la convocatoria ${c.anio_academico}.`, recargar)}
          />
        ) : null)
      }
      permisos={{ crear: puedeGestionar, editar: puedeGestionar, eliminar: puedeGestionar }}
    />
  )
}
