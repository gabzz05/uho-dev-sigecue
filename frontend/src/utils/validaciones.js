// Mismas reglas que el backend, para avisar antes de enviar (RG-002).
export const PATRON_CI = /^\d{11}$/
export const PATRON_CELULAR = /^5\d{7}$/
export const PATRON_EMAIL = /^\S+@\S+\.\S+$/
const MIN_PASSWORD = 8

export const MENSAJE_CI = 'El carnet de identidad debe tener 11 dígitos, sin espacios ni guiones.'
export const MENSAJE_CELULAR = 'El celular debe tener 8 dígitos y empezar por 5.'

export function validarPassword(password, confirmacion) {
  const errores = {}
  if (password.length < MIN_PASSWORD) errores.password = `La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`
  if (confirmacion !== password) errores.confirmacion = 'Las contraseñas no coinciden.'
  return errores
}

export function validarRegistro(v) {
  const errores = validarPassword(v.password, v.confirmacion)
  if (!v.nombre.trim()) errores.nombre = 'Escribe tu nombre.'
  if (!v.apellidos.trim()) errores.apellidos = 'Escribe tus apellidos.'
  if (!PATRON_CI.test(v.ci)) errores.ci = MENSAJE_CI
  if (!PATRON_EMAIL.test(v.email)) errores.email = 'Escribe un correo electrónico válido.'
  if (!PATRON_CELULAR.test(v.celular)) errores.celular = MENSAJE_CELULAR
  if (!v.acepta_privacidad) errores.acepta_privacidad = 'Debes aceptar la política de privacidad para registrarte.'
  return errores
}

/** Datos que espera `POST /auth/registro/` (sin la confirmación de contraseña). */
export function datosDeRegistro(v) {
  return {
    nombre: v.nombre.trim(),
    apellidos: v.apellidos.trim(),
    ci: v.ci,
    email: v.email.trim(),
    celular: v.celular,
    password: v.password,
    acepta_privacidad: v.acepta_privacidad,
  }
}
