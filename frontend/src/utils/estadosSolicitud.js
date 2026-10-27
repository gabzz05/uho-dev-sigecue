/** Estados de la solicitud (RF-051) tal como los ven el aspirante y el panel. */
export const ESTADOS_SOLICITUD = {
  borrador: { label: 'Borrador', tone: 'neutral' },
  pendiente: { label: 'Pendiente', tone: 'warning' },
  en_revision: { label: 'En revisión', tone: 'info' },
  observada: { label: 'Observada', tone: 'danger' },
  otorgada: { label: 'Otorgada', tone: 'success' },
  no_seleccionado: { label: 'No seleccionado', tone: 'neutral' },
}

/** Ciclo de una observación (RF-055): solo RESUELTA deja de bloquear el ranking. */
export const ESTADOS_OBSERVACION = {
  abierta: { label: 'Abierta', tone: 'danger' },
  corregida: { label: 'Corregida, por verificar', tone: 'warning' },
  reabierta: { label: 'Reabierta', tone: 'danger' },
  resuelta: { label: 'Resuelta', tone: 'success' },
}

/** Índice para mostrar: el validado o, si falta, el declarado (marcado como tal). */
export function textoIndice({ indice_validado: validado, indice_declarado: declarado }) {
  if (validado != null) return String(validado)
  return declarado != null ? `${declarado} (declarado)` : '—'
}
