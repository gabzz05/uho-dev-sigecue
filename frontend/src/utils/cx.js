/** Une nombres de clase ignorando los valores falsos. */
export function cx(...clases) {
  return clases.filter(Boolean).join(' ')
}
