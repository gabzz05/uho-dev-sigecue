import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { INTERVALO_POLLING_MS, NotificacionesProvider, useNotificaciones } from '../../hooks/useNotificaciones'
import * as auth from '../../services/auth'
import * as nomencladores from '../../services/nomencladores'
import { envios, notificaciones } from '../../services/notificaciones'
import { usuarios } from '../../services/usuarios'
import { ASPIRANTE, perfil, renderApp } from '../../test/renderApp'

vi.mock('../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../services/notificaciones', () => ({
  notificaciones: { ruta: '/notificaciones/', noLeidas: vi.fn(), listar: vi.fn(), leer: vi.fn(), leerTodas: vi.fn(), eliminar: vi.fn() },
  envios: { ruta: '/admin/notificaciones/envios/', listar: vi.fn(), crear: vi.fn(), contar: vi.fn() },
}))
vi.mock('../../services/usuarios', () => ({ usuarios: { rolesAsignables: vi.fn() }, roles: {} }))
vi.mock('../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn() })
  return { facultades: recurso('f'), cumFum: recurso('c'), municipios: recurso('m'), areas: recurso('a'), departamentos: recurso('d'), cargos: recurso('g'), carreras: recurso('r') }
})

const pagina = (results) => ({ count: results.length, results })
const AVISO = { id: 1, asunto: 'Convocatoria abierta', resumen: 'Ya puedes solicitar…', cuerpo: 'Ya puedes solicitar tu carrera.', leida: false, created_at: new Date().toISOString() }
const LEIDO = { ...AVISO, id: 2, asunto: 'Bienvenida', leida: true }

beforeEach(() => {
  vi.clearAllMocks()
  notificaciones.noLeidas.mockResolvedValue(1)
  notificaciones.listar.mockResolvedValue(pagina([AVISO, LEIDO]))
  notificaciones.leer.mockImplementation((id) => Promise.resolve({ ...AVISO, id, leida: true }))
  notificaciones.leerTodas.mockResolvedValue({ no_leidas: 0 })
  envios.listar.mockResolvedValue(pagina([]))
  usuarios.rolesAsignables.mockResolvedValue([{ codigo: 'secretario_facultad', nombre: 'Secretario(a) Facultad' }])
  Object.values(nomencladores).forEach((r) => r.listar.mockResolvedValue(pagina([])))
})

afterEach(() => vi.useRealTimers())

describe('polling del contador', () => {
  function Contador() {
    return <span>no leídas: {useNotificaciones().noLeidas}</span>
  }

  it('consulta al montar y cada 60 s', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    render(
      <NotificacionesProvider>
        <Contador />
      </NotificacionesProvider>,
    )
    expect(await screen.findByText('no leídas: 1')).toBeInTheDocument()

    notificaciones.noLeidas.mockResolvedValue(4)
    await act(() => vi.advanceTimersByTimeAsync(INTERVALO_POLLING_MS))

    expect(await screen.findByText('no leídas: 4')).toBeInTheDocument()
  })

  it('no consulta con la pestaña oculta y consulta al volver', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    render(
      <NotificacionesProvider>
        <Contador />
      </NotificacionesProvider>,
    )
    await screen.findByText('no leídas: 1')
    const visibilidad = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    const llamadas = notificaciones.noLeidas.mock.calls.length

    await act(() => vi.advanceTimersByTimeAsync(INTERVALO_POLLING_MS * 3))
    expect(notificaciones.noLeidas.mock.calls.length).toBe(llamadas)

    visibilidad.mockReturnValue('visible')
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    await waitFor(() => expect(notificaciones.noLeidas.mock.calls.length).toBe(llamadas + 1))
  })
})

describe('campana', () => {
  it('muestra el contador y las últimas notificaciones', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante')

    const campana = await screen.findByRole('button', { name: 'Notificaciones: 1 sin leer' })
    fireEvent.click(campana)

    const panel = await screen.findByRole('region', { name: 'Notificaciones recientes' })
    expect(await within(panel).findByText('Convocatoria abierta')).toBeInTheDocument()
    expect(within(panel).getByRole('link', { name: 'Ver todas' })).toHaveAttribute('href', '/aspirante/notificaciones')
  })

  it('abrir una no leída la marca y actualiza el contador', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante')
    fireEvent.click(await screen.findByRole('button', { name: 'Notificaciones: 1 sin leer' }))
    notificaciones.noLeidas.mockResolvedValue(0)

    fireEvent.click(await screen.findByRole('button', { name: /Convocatoria abierta/ }))

    await waitFor(() => expect(notificaciones.leer).toHaveBeenCalledWith(1))
    expect(await screen.findByRole('button', { name: 'Notificaciones' })).toBeInTheDocument()
  })

  it('marcar todas como leídas', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante')
    fireEvent.click(await screen.findByRole('button', { name: 'Notificaciones: 1 sin leer' }))

    fireEvent.click(await screen.findByRole('button', { name: 'Marcar todas como leídas' }))

    await waitFor(() => expect(notificaciones.leerTodas).toHaveBeenCalled())
  })
})

describe('Mis notificaciones', () => {
  it('al desplegar muestra el texto completo y la marca como leída', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante/notificaciones')

    const cabecera = await screen.findByRole('button', { name: /Convocatoria abierta/, expanded: false })
    fireEvent.click(cabecera)

    expect(await screen.findByText('Ya puedes solicitar tu carrera.')).toBeInTheDocument()
    expect(notificaciones.leer).toHaveBeenCalledWith(1)
  })

  it('una ya leída no se vuelve a marcar', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante/notificaciones')

    fireEvent.click(await screen.findByRole('button', { name: /Bienvenida/ }))

    expect(notificaciones.leer).not.toHaveBeenCalled()
  })

  it('elimina una notificación', async () => {
    notificaciones.eliminar.mockResolvedValue()
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante/notificaciones')

    fireEvent.click(await screen.findByRole('button', { name: /Bienvenida/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar' }))

    await waitFor(() => expect(notificaciones.eliminar).toHaveBeenCalledWith(2))
    expect(await screen.findByText('Notificación eliminada.')).toBeInTheDocument()
  })

  it('filtra las no leídas', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    renderApp('/aspirante/notificaciones')

    fireEvent.change(await screen.findByLabelText('Mostrar'), { target: { value: 'false' } })

    await waitFor(() => expect(notificaciones.listar).toHaveBeenLastCalledWith({ leida: 'false', page: 1, page_size: 20 }))
  })
})

describe('Envíos masivos', () => {
  const GLOBAL = perfil({ permisos: ['notificaciones.ver', 'notificaciones.crear'] })
  const LOCAL = perfil({
    rol: { codigo: 'admin_facultad', nombre: 'Admin Facultad', ambito: 'facultad' },
    entidad: { tipo: 'facultad', id: 3, nombre: 'Fac. Informática' },
    permisos: ['notificaciones.ver', 'notificaciones.crear'],
  })

  async function abrirFormulario(usuario) {
    auth.restaurarSesion.mockResolvedValue(usuario)
    renderApp('/admin/envios')
    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo envío' }))
    return screen.getByRole('dialog', { name: 'Nuevo envío masivo' })
  }

  it('solo los roles globales ofrecen "Todos los aspirantes"', async () => {
    const dialogo = await abrirFormulario(LOCAL)

    const tipos = within(within(dialogo).getByLabelText('Destinatarios')).getAllByRole('option').map((o) => o.textContent)
    expect(tipos).toEqual(['Selecciona…', 'Usuarios de un rol', 'Usuarios de Fac. Informática'])
  })

  it('cuenta los destinatarios, confirma y envía', async () => {
    envios.contar.mockResolvedValue({ destinatarios: 120, descripcion: 'Todos los aspirantes' })
    envios.crear.mockResolvedValue({ id: 1, destinatarios: 120 })
    const dialogo = await abrirFormulario(GLOBAL)

    fireEvent.change(within(dialogo).getByLabelText('Destinatarios'), { target: { value: 'aspirantes' } })
    expect(await within(dialogo).findByText('Todos los aspirantes: 120 destinatario(s).')).toBeInTheDocument()
    fireEvent.change(within(dialogo).getByLabelText('Asunto'), { target: { value: 'Aviso' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Mensaje/), { target: { value: 'Hola {{ nombre }}' } })
    fireEvent.click(within(dialogo).getByLabelText(/también por correo/))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Enviar' }))

    const confirmacion = await screen.findByRole('dialog', { name: 'Confirmar envío' })
    expect(confirmacion).toHaveTextContent('Se notificará a 120 destinatario(s), también por correo.')
    fireEvent.click(within(confirmacion).getByRole('button', { name: 'Enviar' }))

    await waitFor(() =>
      expect(envios.crear).toHaveBeenCalledWith({ grupo: { tipo: 'aspirantes' }, asunto: 'Aviso', cuerpo: 'Hola {{ nombre }}', por_correo: true }),
    )
    expect(await screen.findByText('Notificación enviada a 120 destinatario(s).')).toBeInTheDocument()
  })

  it('valida antes de confirmar', async () => {
    const dialogo = await abrirFormulario(GLOBAL)

    fireEvent.click(within(dialogo).getByRole('button', { name: 'Enviar' }))

    expect(await within(dialogo).findByText('Selecciona a quién va dirigido.')).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Confirmar envío' })).not.toBeInTheDocument()
  })

  it('un rol local envía a su entidad sin elegirla', async () => {
    envios.contar.mockResolvedValue({ destinatarios: 4, descripcion: 'Usuarios de Fac. Informática' })
    const dialogo = await abrirFormulario(LOCAL)

    fireEvent.change(within(dialogo).getByLabelText('Destinatarios'), { target: { value: 'entidad' } })

    await waitFor(() => expect(envios.contar).toHaveBeenCalledWith({ tipo: 'entidad' }))
    expect(within(dialogo).queryByLabelText('Entidad')).not.toBeInTheDocument()
  })
})
