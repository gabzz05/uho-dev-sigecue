import { api } from './api'

/** Actualiza celular y/o foto del usuario autenticado. La foto se envía como multipart. */
export async function actualizarPerfil({ celular, foto }) {
  const datos = new FormData()
  if (celular !== undefined) datos.append('celular', celular)
  if (foto) datos.append('foto', foto)
  const { data } = await api.patch('/auth/me/', datos)
  return data
}

export async function cambiarPassword(actual, nueva) {
  await api.post('/auth/me/password/', { actual, nueva })
}
