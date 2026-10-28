import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../services/auth'
import { obtenerDashboard } from '../../services/dashboard'
import { perfil, renderApp } from '../../test/renderApp'

vi.mock('../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../services/dashboard', () => ({ obtenerDashboard: vi.fn() }))

const JEFE = perfil({ permisos: ['dashboard.ver', 'solicitudes.ver', 'otorgamiento.ver'] })

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue(JEFE)
})

describe('dashboard principal', () => {
  it('muestra las alertas, las secciones y los accesos del rol', async () => {
    obtenerDashboard.mockResolvedValue({
      secciones: {
        solicitudes: { convocatoria: '1.ª 2026-2027', estado_convocatoria: 'Abierta', fecha_cierre: '2026-11-30', total: 12, por_estado: { pendiente: 8, observada: 4 } },
        otorgamiento: { convocatoria: '1.ª 2026-2027', estado: 'Sin generar', otorgadas: null },
      },
      alertas: [
        { nivel: 'atencion', texto: '4 solicitud(es) observadas esperan la corrección del aspirante.', enlace: '/admin/solicitudes' },
        { nivel: 'aviso', texto: 'La convocatoria de solicitud 1.ª 2026-2027 cierra en 2 día(s).', enlace: '/admin/convocatorias' },
      ],
      actualizado: '2026-11-28T10:00:00Z',
    })
    renderApp('/admin')

    expect(await screen.findByText('Requiere atención')).toBeInTheDocument()
    expect(screen.getByText(/4 solicitud\(es\) observadas/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Ir/ })[0]).toHaveAttribute('href', '/admin/solicitudes')
    expect(screen.getByText('Observada')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir Otorgamiento' })).toHaveAttribute('href', '/admin/otorgamiento')
    const accesos = screen.getByRole('navigation', { name: 'Accesos rápidos' })
    expect(accesos).toHaveTextContent('Solicitudes')
    expect(accesos).not.toHaveTextContent('Usuarios')
  })

  it('sin procesos en marcha lo indica', async () => {
    obtenerDashboard.mockResolvedValue({ secciones: {}, alertas: [], actualizado: '2026-11-28T10:00:00Z' })
    renderApp('/admin')

    expect(await screen.findByText('Todavía no hay procesos en marcha que mostrar.')).toBeInTheDocument()
    expect(screen.queryByText('Requiere atención')).not.toBeInTheDocument()
  })
})
