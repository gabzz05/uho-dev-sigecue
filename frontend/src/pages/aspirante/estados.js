/** Estados de la solicitud que ve el aspirante (RF-051). */
export const ESTADOS_SOLICITUD = {
  borrador: { label: 'Borrador', tone: 'neutral' },
  pendiente: { label: 'Pendiente', tone: 'warning' },
  en_revision: { label: 'En revisión', tone: 'info' },
  otorgada: { label: 'Otorgada', tone: 'success' },
  no_seleccionado: { label: 'No seleccionado', tone: 'danger' },
}

/**
 * La solicitud que se muestra al aspirante (la API las ordena de nueva a antigua).
 * Con una convocatoria abierta: la de esa convocatoria; si no tiene y quedó
 * "no seleccionado" en la anterior (o la dejó en borrador), ninguna: puede
 * presentar una nueva (RF-062).
 * Sin convocatoria abierta: la más reciente.
 */
export function solicitudVigente(lista, hayConvocatoriaAbierta) {
  const enCurso = lista.find((s) => s.convocatoria.acepta_solicitudes)
  if (enCurso) return enCurso
  const ultima = lista[0] ?? null
  if (hayConvocatoriaAbierta && ['borrador', 'no_seleccionado'].includes(ultima?.estado)) return null
  return ultima
}
