import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { logs } from '../../../services/auditoria'
import * as auth from '../../../services/auth'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/auditoria', () => ({ logs: { ruta: '/admin/logs/', listar: vi.fn(), modulos: vi.fn() } }))

const REGISTRO = {
  id: 7, created_at: '2026-10-24T10:00:00Z', usuario: 1, usuario_nombre: 'jcastro', accion: 'POST api/v1/admin/usuarios/',
  modulo: 'usuarios', entidad_afectada: '', entidad_id: '', metodo: 'POST', ruta: '/api/v1/admin/usuarios/',
  ip: '10.0.0.5', resultado: 'error', codigo_http: 400, detalle: { motivo: 'prueba' },
}

beforeEach(() => {
  vi.clearAllMocks()
  logs.listar.mockResolvedValue({ count: 1, results: [REGISTRO] })
  logs.modulos.mockResolvedValue(['auth', 'usuarios'])
  auth.restaurarSesion.mockResolvedValue(perfil({ permisos: ['logs.ver'] }))
})

describe('Logs de auditoría', () => {
  it('lista los registros sin acciones de edición', async () => {
    renderApp('/admin/logs')

    const fila = (await screen.findByText('POST api/v1/admin/usuarios/')).closest('tr')
    expect(within(fila).getByText('jcastro')).toBeInTheDocument()
    expect(within(fila).getByText('Error')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Editar|Eliminar/ })).not.toBeInTheDocument()
  })

  it('filtra por módulo, resultado y fechas', async () => {
    renderApp('/admin/logs')
    await screen.findByRole('option', { name: 'usuarios' })

    fireEvent.change(screen.getByLabelText('Módulo'), { target: { value: 'usuarios' } })
    fireEvent.change(screen.getByLabelText('Resultado'), { target: { value: 'error' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-10-01' } })

    await waitFor(() =>
      expect(logs.listar).toHaveBeenLastCalledWith({ modulo: 'usuarios', resultado: 'error', desde: '2026-10-01', page: 1, page_size: 20 }),
    )
  })

  it('muestra el detalle completo de un registro', async () => {
    renderApp('/admin/logs')

    fireEvent.click(await screen.findByRole('button', { name: 'Ver detalle del registro 7' }))

    const dialogo = screen.getByRole('dialog', { name: 'Registro de auditoría' })
    expect(within(dialogo).getByText('10.0.0.5')).toBeInTheDocument()
    expect(within(dialogo).getByText('POST /api/v1/admin/usuarios/')).toBeInTheDocument()
    expect(within(dialogo).getByText(/"motivo": "prueba"/)).toBeInTheDocument()
  })

  it('sin el permiso no se muestra', async () => {
    auth.restaurarSesion.mockResolvedValue(perfil({ permisos: ['dashboard.ver'] }))
    renderApp('/admin/logs')

    expect(await screen.findByText('No tienes permiso para ver esta sección')).toBeInTheDocument()
    expect(logs.listar).not.toHaveBeenCalled()
  })
})
