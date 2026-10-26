import { Gavel, MessageSquareReply, Pencil, Plus, Trash2, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { RecursoModal } from '../../../components/crud/RecursoModal'
import { Badge, Button, DataTable, StatusBadge, TableFooter, useToast, VisuallyHidden } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { mensajeDeError } from '../../../services/errores'
import { carreras, cumFum, facultades } from '../../../services/nomencladores'
import { lineasPlan } from '../../../services/planPlazas'
import { ACCION_ENTIDAD } from './estados'
import styles from './Plan.module.css'

const ACCIONES_RESPUESTA = [
  { value: 'aceptar', label: 'Aceptar la propuesta de la CI' },
  { value: 'modificar', label: 'Modificar la cantidad' },
  { value: 'quitar', label: 'Solicitar quitar la carrera' },
]
const DECISIONES = [
  { value: 'aceptar', label: 'Aceptar la propuesta de la entidad' },
  { value: 'mantener', label: 'Mantener la propuesta inicial de la CI' },
  { value: 'otro', label: 'Fijar otra cantidad' },
]

const numero = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const plazasValidas = (v) => v !== '' && Number.isInteger(Number(v)) && Number(v) >= 0
const texto = (valor) => (valor === null || valor === undefined ? 'Fuera del plan' : valor)

/** Modales de cada acción sobre una línea: esquema, validación y llamada a la API. */
function modalPara(tipo, linea, contexto) {
  switch (tipo) {
    case 'editar':
      return {
        titulo: `Propuesta inicial — ${linea.carrera_nombre}`,
        campos: [{ name: 'plazas', label: 'Plazas', type: 'number', min: 0, required: true, ancho: 'mitad' }],
        iniciales: { plazas: String(linea.plazas_propuestas) },
        validar: (v) => (plazasValidas(v.plazas) ? {} : { plazas: 'Indica un número de plazas (0 o más).' }),
        guardar: (v) => lineasPlan.actualizar(linea.id, Number(v.plazas)),
      }
    case 'responder':
      return {
        titulo: `Responder — ${linea.carrera_nombre}`,
        campos: (v) => [
          { name: 'accion', label: 'Respuesta de la entidad', type: 'select', options: ACCIONES_RESPUESTA, required: true },
          ...(v.accion === 'modificar' ? [{ name: 'plazas', label: 'Plazas que propone la entidad', type: 'number', min: 0, required: true, ancho: 'mitad' }] : []),
          ...(v.accion !== 'aceptar' ? [{ name: 'comentario', label: 'Justificación', type: 'textarea', required: true, hint: 'Obligatoria para cualquier cambio (RF-034).' }] : []),
        ],
        iniciales: {
          accion: linea.accion_entidad === 'agregar' ? 'aceptar' : linea.accion_entidad,
          plazas: linea.plazas_entidad ?? '',
          comentario: linea.comentario_entidad,
        },
        validar: (v) => ({
          ...(v.accion === 'modificar' && !plazasValidas(v.plazas) ? { plazas: 'Indica un número de plazas (0 o más).' } : {}),
          ...(v.accion !== 'aceptar' && !v.comentario.trim() ? { comentario: 'Justifica el cambio.' } : {}),
        }),
        guardar: (v) => lineasPlan.responder(linea.id, { accion: v.accion, plazas: numero(v.plazas), comentario: v.comentario }),
      }
    case 'decidir':
      return {
        titulo: `Decisión de la CI — ${linea.carrera_nombre}`,
        campos: (v) => [
          { name: 'decision', label: 'Decisión', type: 'select', options: DECISIONES, required: true },
          ...(v.decision === 'otro' ? [{ name: 'plazas', label: 'Plazas', type: 'number', min: 0, required: true, ancho: 'mitad' }] : []),
          { name: 'comentario', label: 'Comentario', type: 'textarea', required: v.decision !== 'aceptar', hint: 'Obligatorio si no aceptas la propuesta (RF-035).' },
        ],
        iniciales: { decision: linea.decision_ci, plazas: linea.plazas_decision ?? '', comentario: linea.comentario_ci },
        validar: (v) => ({
          ...(v.decision === 'otro' && !plazasValidas(v.plazas) ? { plazas: 'Indica un número de plazas (0 o más).' } : {}),
          ...(v.decision !== 'aceptar' && !v.comentario.trim() ? { comentario: 'Justifica la decisión.' } : {}),
        }),
        guardar: (v) => lineasPlan.decidir(linea.id, { decision: v.decision, plazas: numero(v.plazas), comentario: v.comentario }),
      }
    case 'agregar':
      return contexto.esCI
        ? {
            titulo: 'Agregar carrera al plan',
            campos: [
              { name: 'carrera', label: 'Carrera', type: 'select', options: contexto.opcionesCarrera, required: true },
              { name: 'entidad', label: 'Facultad o CUM/FUM', type: 'select', options: contexto.entidades, required: true },
              { name: 'plazas', label: 'Plazas', type: 'number', min: 0, required: true, ancho: 'mitad' },
            ],
            iniciales: { carrera: '', entidad: '', plazas: '' },
            validar: (v) => ({
              ...(!v.carrera ? { carrera: 'Selecciona la carrera.' } : {}),
              ...(!v.entidad ? { entidad: 'Selecciona la entidad.' } : {}),
              ...(!plazasValidas(v.plazas) ? { plazas: 'Indica un número de plazas (0 o más).' } : {}),
            }),
            guardar: (v) => {
              const [campo, id] = v.entidad.split(':')
              return lineasPlan.crear({ plan: contexto.plan.id, carrera: v.carrera, [campo]: id, plazas: Number(v.plazas) })
            },
          }
        : {
            titulo: 'Solicitar agregar una carrera',
            campos: [
              { name: 'carrera', label: 'Carrera del catálogo', type: 'select', options: contexto.opcionesCarrera, required: true },
              { name: 'plazas', label: 'Plazas que propone la entidad', type: 'number', min: 0, required: true, ancho: 'mitad' },
              { name: 'comentario', label: 'Justificación', type: 'textarea', required: true },
            ],
            iniciales: { carrera: '', plazas: '', comentario: '' },
            validar: (v) => ({
              ...(!v.carrera ? { carrera: 'Selecciona la carrera.' } : {}),
              ...(!plazasValidas(v.plazas) ? { plazas: 'Indica un número de plazas (0 o más).' } : {}),
              ...(!v.comentario.trim() ? { comentario: 'Justifica la solicitud.' } : {}),
            }),
            guardar: (v) => lineasPlan.crear({ plan: contexto.plan.id, carrera: v.carrera, plazas: Number(v.plazas), comentario: v.comentario }),
          }
    default:
      return null
  }
}

/** Tabla de líneas del plan con las acciones que el usuario puede hacer en este estado. */
export function LineasPlan({ plan, lineas, onCambio }) {
  const { esGlobal } = useAuth()
  const toast = useToast()
  const [modal, setModal] = useState(null) // { tipo, linea }
  const acciones = new Set(plan.acciones)
  const opcionesCarrera = useOpciones(acciones.has('editar_lineas') || acciones.has('responder') ? carreras : null)
  const opcionesFacultad = useOpciones(acciones.has('editar_lineas') ? facultades : null)
  const opcionesCum = useOpciones(acciones.has('editar_lineas') ? cumFum : null)
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]

  async function quitar(linea) {
    try {
      await lineasPlan.eliminar(linea.id)
      toast.exito(`Se quitó ${linea.carrera_nombre}.`)
      onCambio()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  const finalizado = plan.estado === 'en_aprobacion' || plan.estado === 'publicado'
  const columnas = [
    { key: 'carrera', header: 'Carrera', render: (l) => <strong>{l.carrera_nombre}</strong> },
    { key: 'entidad', header: 'Entidad', render: (l) => l.entidad?.nombre },
    { key: 'propuesta_ci', header: 'Propuesta CI', align: 'center', render: (l) => (l.origen === 'entidad' ? '—' : l.plazas_propuestas) },
  ]
  if (plan.estado !== 'borrador') {
    columnas.push({
      key: 'entidad_propone',
      header: 'Propuesta de la entidad',
      render: (l) => (
        <div className={styles.celda}>
          <span>
            <StatusBadge estado={l.accion_entidad} mapa={ACCION_ENTIDAD} />{' '}
            {l.accion_entidad !== 'aceptar' && <strong>{texto(l.propuesta_entidad)}</strong>}
          </span>
          {l.comentario_entidad && <small>{l.comentario_entidad}</small>}
        </div>
      ),
    })
  }
  if (['revision_ci', 'en_aprobacion', 'publicado'].includes(plan.estado)) {
    columnas.push({
      key: 'decision',
      header: finalizado ? 'Plazas aprobadas' : 'Resultado',
      align: 'center',
      render: (l) => (
        <div className={styles.celda}>
          <strong>{texto(finalizado ? l.plazas_aprobadas : l.resultado)}</strong>
          {l.decision_ci !== 'aceptar' && <Badge tone="warning">{l.decision_ci_nombre}</Badge>}
          {l.comentario_ci && <small>{l.comentario_ci}</small>}
        </div>
      ),
    })
  }
  columnas.push({
    key: 'acciones',
    header: <VisuallyHidden>Acciones</VisuallyHidden>,
    align: 'right',
    render: (l) => (
      <div className={styles.acciones}>
        {acciones.has('editar_lineas') && (
          <>
            <Button variant="ghost" size="sm" icon={Pencil} aria-label={`Editar ${l.carrera_nombre} (${l.entidad?.nombre})`} onClick={() => setModal({ tipo: 'editar', linea: l })} />
            <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Quitar ${l.carrera_nombre} (${l.entidad?.nombre})`} onClick={() => quitar(l)} />
          </>
        )}
        {acciones.has('responder') && l.origen === 'ci' && (
          <Button variant="ghost" size="sm" icon={MessageSquareReply} aria-label={`Responder ${l.carrera_nombre}`} onClick={() => setModal({ tipo: 'responder', linea: l })} />
        )}
        {acciones.has('responder') && l.origen === 'entidad' && (
          <Button variant="ghost" size="sm" icon={Undo2} aria-label={`Retirar la solicitud de ${l.carrera_nombre}`} onClick={() => quitar(l)} />
        )}
        {acciones.has('decidir') && (
          <Button variant="ghost" size="sm" icon={Gavel} aria-label={`Decidir ${l.carrera_nombre} (${l.entidad?.nombre})`} onClick={() => setModal({ tipo: 'decidir', linea: l })} />
        )}
      </div>
    ),
  })

  const total = lineas.reduce((suma, l) => suma + (finalizado ? (l.plazas_aprobadas ?? 0) : plan.estado === 'borrador' ? l.plazas_propuestas : (l.resultado ?? l.propuesta_entidad ?? 0)), 0)
  const config = modal && modalPara(modal.tipo, modal.linea, { plan, esCI: esGlobal, opcionesCarrera, entidades })

  return (
    <>
      {(acciones.has('editar_lineas') || acciones.has('responder')) && (
        <div className={styles.barraTabla}>
          <Button variant="secondary" icon={Plus} onClick={() => setModal({ tipo: 'agregar', linea: null })}>
            {acciones.has('editar_lineas') ? 'Agregar carrera' : 'Solicitar carrera'}
          </Button>
        </div>
      )}
      <DataTable columns={columnas} rows={lineas} emptyMessage="El plan todavía no tiene carreras." />
      <TableFooter>
        <span>
          {lineas.length} carrera(s) · Total: <strong>{total}</strong> plazas
        </span>
      </TableFooter>
      {config && (
        <RecursoModal
          key={`${modal.tipo}-${modal.linea?.id ?? 'nueva'}`}
          open
          titulo={config.titulo}
          campos={config.campos}
          valoresIniciales={config.iniciales}
          validar={config.validar}
          onGuardar={config.guardar}
          onClose={(guardado) => {
            setModal(null)
            if (guardado) {
              toast.exito('Los cambios se guardaron.')
              onCambio()
            }
          }}
        />
      )}
    </>
  )
}
