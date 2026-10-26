const LOCALE = 'es-CU'

/** "2026-12-15" → "15/12/2026" (sin desplazar el día por la zona horaria). */
export function formatearFecha(fechaIso) {
  if (!fechaIso) return ''
  const [anio, mes, dia] = fechaIso.slice(0, 10).split('-')
  return `${dia}/${mes}/${anio}`
}

export function formatearFechaHora(iso) {
  return iso ? new Date(iso).toLocaleString(LOCALE, { dateStyle: 'short', timeStyle: 'short' }) : ''
}

/** "hace 5 min", "hace 3 h", "hace 2 días"; más de una semana: la fecha. */
export function haceCuanto(iso, ahora = Date.now()) {
  const segundos = Math.max(0, Math.round((ahora - new Date(iso).getTime()) / 1000))
  if (segundos < 60) return 'ahora'
  if (segundos < 3600) return `hace ${Math.floor(segundos / 60)} min`
  if (segundos < 86400) return `hace ${Math.floor(segundos / 3600)} h`
  const dias = Math.floor(segundos / 86400)
  if (dias < 7) return dias === 1 ? 'ayer' : `hace ${dias} días`
  return new Date(iso).toLocaleDateString(LOCALE)
}
