/** Estados de la prematrícula (RF-068). Incompleta no es renuncia: la plaza se conserva. */
export const ESTADOS_PREMATRICULA = {
  pendiente: { label: 'Pendiente', tone: 'neutral' },
  borrador: { label: 'Borrador', tone: 'info' },
  completada: { label: 'Completada', tone: 'warning' },
  con_correcciones: { label: 'Con correcciones', tone: 'danger' },
  aprobada: { label: 'Aprobada', tone: 'success' },
  incompleta: { label: 'Incompleta', tone: 'danger' },
}

/** Revisión de cada documento o campo. */
export const REVISION_ELEMENTO = {
  pendiente: { label: 'Por revisar', tone: 'neutral' },
  aprobado: { label: 'Aprobado', tone: 'success' },
  rechazado: { label: 'Rechazado', tone: 'danger' },
}
