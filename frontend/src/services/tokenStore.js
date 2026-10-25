/**
 * Access token en memoria (nunca en localStorage): un XSS no puede leerlo de
 * almacenamiento persistente y desaparece al cerrar la pestaña. La sesión se
 * recupera al recargar gracias a la cookie httpOnly de refresh.
 */
let access = null

export const tokenStore = {
  get: () => access,
  set: (token) => {
    access = token
  },
  clear: () => {
    access = null
  },
}
