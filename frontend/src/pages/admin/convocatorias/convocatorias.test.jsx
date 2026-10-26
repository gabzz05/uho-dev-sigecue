import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import { convocatoriasSolicitud } from '../../../services/convocatorias'
import * as nomencladores from '../../../services/nomencladores'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/convocatorias', () => ({
  convocatoriasSolicitud: { ruta: '/c/', listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn(), abrir: vi.fn(), cerrar: vi.fn() },
}))
vi.mock('../../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn() })
  return {
    facultades: recurso('f'), cumFum: recurso('c'), carreras: recurso('r'), municipios: recurso('m'),
    areas: recurso('a'), departamentos: recurso('d'), cargos: recurso('g'),
  }
})

const BORRADOR = {
  id: 1, anio_academico: '2026-2027', numero: 1, fecha_inicio: '2026-11-01', fecha_cierre: '2026-11-30', mensaje_publico: '',
  estado: 'borrador', estado_nombre: 'Borrador', facultades: [], cum_fums: [], entidades: [], total_ofertas: 4, interesados_notificados: null,
}
const JEFE_CI = perfil({ permisos: ['convocatorias.ver', 'convocatorias.crear', 'convocatorias.editar', 'convocatorias.eliminar'] })

beforeEach(() => {
  vi.clearAllMocks()
  convocatoriasSolicitud.listar.mockResolvedValue({ count: 1, results: [BORRADOR] })
  nomencladores.facultades.listar.mockResolvedValue({ count: 1, results: [{ id: 3, nombre: 'Fac. Informática' }] })
  nomencladores.cumFum.listar.mockResolvedValue({ count: 1, results: [{ id: 5, nombre: 'CUM Moa' }] })
})

async function abrir(usuario = JEFE_CI) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp('/admin/convocatorias')
  await screen.findByText('Todas las que tienen plazas')
}

describe('convocatorias de solicitud', () => {
  it('crea una convocatoria con entidades seleccionadas', async () => {
    convocatoriasSolicitud.crear.mockResolvedValue({ ...BORRADOR, id: 2 })
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) convocatoria/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Año académico/), { target: { value: '2026-2027' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Fecha de inicio/), { target: { value: '2026-11-01' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Fecha de cierre/), { target: { value: '2026-11-30' } })
    fireEvent.click(await within(dialogo).findByLabelText('CUM Moa'))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() =>
      expect(convocatoriasSolicitud.crear).toHaveBeenCalledWith({
        anio_academico: '2026-2027', fecha_inicio: '2026-11-01', fecha_cierre: '2026-11-30', mensaje_publico: '',
        facultades: [], cum_fums: [5],
      }),
    )
  })

  it('abrir la primera avisa que se notificará a los interesados', async () => {
    convocatoriasSolicitud.abrir.mockResolvedValue({ ...BORRADOR, estado: 'abierta' })
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Abrir la convocatoria 1.ª 2026-2027' }))
    const dialogo = screen.getByRole('dialog', { name: 'Abrir convocatoria' })
    expect(dialogo).toHaveTextContent('se avisará por correo a quienes expresaron interés')
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Abrir convocatoria' }))

    await waitFor(() => expect(convocatoriasSolicitud.abrir).toHaveBeenCalledWith(1))
  })

  it('muestra el error si falta el plan de plazas publicado', async () => {
    convocatoriasSolicitud.abrir.mockRejectedValue({
      response: { data: { error: { mensaje: 'El plan de plazas 2026-2027 todavía no está publicado.' } } },
    })
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Abrir la convocatoria 1.ª 2026-2027' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Abrir convocatoria' }))

    expect(await screen.findByText('El plan de plazas 2026-2027 todavía no está publicado.')).toBeInTheDocument()
  })

  it('un rol local solo consulta', async () => {
    await abrir(perfil({ rol: { codigo: 'admin_facultad', nombre: 'Admin', ambito: 'facultad' }, permisos: ['convocatorias.ver'] }))

    expect(screen.queryByRole('button', { name: /Nuevo\(a\) convocatoria/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Abrir la convocatoria/ })).not.toBeInTheDocument()
  })
})
