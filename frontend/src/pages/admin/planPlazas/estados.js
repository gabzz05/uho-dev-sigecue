/** Estados del plan, en el orden del flujo (sección 7.3). */
export const PASOS_PLAN = [
  { estado: 'borrador', label: 'Borrador de la CI' },
  { estado: 'enviado', label: 'Revisión de las entidades' },
  { estado: 'revision_ci', label: 'Revisión de la CI' },
  { estado: 'en_aprobacion', label: 'Aprobación del Vicerrector' },
  { estado: 'publicado', label: 'Publicado' },
]

export const ESTADO_PLAN = {
  borrador: { label: 'Borrador', tone: 'neutral' },
  enviado: { label: 'Enviado a entidades', tone: 'info' },
  revision_ci: { label: 'Revisión de la CI', tone: 'warning' },
  en_aprobacion: { label: 'En aprobación', tone: 'warning' },
  publicado: { label: 'Publicado', tone: 'success' },
}

export const ESTADO_ENTIDAD = {
  pendiente: { label: 'Pendiente', tone: 'neutral' },
  en_revision: { label: 'En revisión', tone: 'info' },
  propuesta_enviada: { label: 'Propuesta enviada', tone: 'success' },
}

export const ACCION_ENTIDAD = {
  aceptar: { label: 'Acepta', tone: 'neutral' },
  modificar: { label: 'Modifica', tone: 'warning' },
  quitar: { label: 'Pide quitar', tone: 'danger' },
  agregar: { label: 'Pide agregar', tone: 'info' },
}

/** Pasos del Stepper a partir del estado actual. */
export function pasosDe(estado) {
  const actual = PASOS_PLAN.findIndex((p) => p.estado === estado)
  return PASOS_PLAN.map((paso, i) => ({
    label: paso.label,
    estado: i < actual || estado === 'publicado' ? 'completado' : i === actual ? 'actual' : 'pendiente',
  }))
}
