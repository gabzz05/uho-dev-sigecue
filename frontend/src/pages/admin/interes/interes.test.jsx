import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import { convocatoriasInteres, expresiones, ofertas } from '../../../services/interes'
import * as nomencladores from '../../../services/nomencladores'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/interes', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn() })
  return {
    convocatoriasInteres: { ...recurso('/c/'), abrir: vi.fn(), cerrar: vi.fn() },
    ofertas: recurso('/o/'),
    expresiones: { ...recurso('/e/'), exportar: vi.fn(), estadisticas: vi.fn() },
  }
})
vi.mock('../../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn() })
  return { carreras: recurso('r'), facultades: recurso('f'), cumFum: recurso('c'), municipios: recurso('m'), areas: recurso('a'), departamentos: recurso('d'), cargos: recurso('g') }
})

const pagina = (results) => ({ count: results.length, results })
const BORRADOR = { id: 1, anio_academico: '2026-2027', fecha_inicio: '2026-10-01', fecha_cierre: '2026-12-15', mensaje_publico: '', estado: 'borrador', estado_nombre: 'Borrador', total_ofertas: 2, total_interesados: 0 }
const CERRADA = { ...BORRADOR, id: 2, anio_academico: '2025-2026', estado: 'cerrada', estado_nombre: 'Cerrada' }
const OFERTA_CI = { id: 7, carrera_nombre: 'Derecho', entidad: { nombre: 'Fac. Informática', municipio: 'Holguín' }, asignada_por_ci: true, total_interesados: 3 }
const OFERTA_PROPIA = { ...OFERTA_CI, id: 8, carrera_nombre: 'Contabilidad', asignada_por_ci: false }

const JEFE_CI = perfil({ permisos: ['interes.ver', 'interes.crear', 'interes.editar', 'interes.eliminar', 'interes.exportar'] })
const ADMIN_LOCAL = perfil({
  rol: { codigo: 'admin_facultad', nombre: 'Admin Facultad', ambito: 'facultad' },
  entidad: { tipo: 'facultad', id: 3, nombre: 'Fac. Informática' },
  permisos: ['interes.ver', 'interes.crear', 'interes.editar', 'interes.exportar'],
})

beforeEach(() => {
  vi.clearAllMocks()
  convocatoriasInteres.listar.mockResolvedValue(pagina([BORRADOR, CERRADA]))
  ofertas.listar.mockResolvedValue(pagina([OFERTA_CI, OFERTA_PROPIA]))
  expresiones.listar.mockResolvedValue(pagina([{ id: 1, nombre: 'María', ci: '98042512345', celular: '55123456', email: 'm@n.cu', carrera: 'Derecho', entidad: 'Fac', created_at: '2026-10-20T10:00:00Z' }]))
  Object.values(nomencladores).forEach((r) => r.listar.mockResolvedValue(pagina([{ id: 4, nombre: 'Derecho' }])))
})

afterEach(() => vi.restoreAllMocks())

async function abrir(usuario = JEFE_CI) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp('/admin/interes')
  // La pestaña inicial es el dashboard.
  fireEvent.click(await screen.findByRole('tab', { name: 'Convocatorias' }))
  await screen.findByText('2026-2027')
}

const MUNICIPIOS = ['Holguín', 'Banes', 'Moa'].map((nombre, i) => ({ municipio: i + 1, nombre, total: [5, 1, 0][i] }))

describe('dashboard de interés', () => {
  it('muestra totales, barras por entidad y el mapa con su tabla', async () => {
    expresiones.estadisticas.mockResolvedValue({
      total: 6,
      por_carrera: [{ carrera: 'Derecho', total: 4 }, { carrera: 'Contabilidad', total: 2 }],
      por_entidad: [{ entidad: 'Fac. Informática', total: 5 }, { entidad: 'CUM Banes', total: 1 }],
      evolucion: [{ dia: '2026-10-20', total: 6 }],
      por_municipio: MUNICIPIOS,
    })
    auth.restaurarSesion.mockResolvedValue(JEFE_CI)
    renderApp('/admin/interes')

    expect(await screen.findByText('Interés por municipio')).toBeInTheDocument()
    expect(expresiones.estadisticas).toHaveBeenCalledWith({ convocatoria: 1 })
    expect(screen.getByTitle('Holguín: 5 expresiones de interés')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Holguín 5, Banes 1, Moa 0/ })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Expresiones de interés por día' })).toBeInTheDocument()
    // Por entidad: barras ordenadas, no pastel.
    expect(screen.getByTitle('Fac. Informática: 5 expresiones')).toBeInTheDocument()
  })
})

describe('convocatorias', () => {
  it('abre una convocatoria en borrador tras confirmar', async () => {
    convocatoriasInteres.abrir.mockResolvedValue({ ...BORRADOR, estado: 'abierta' })
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Abrir la convocatoria 2026-2027' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Abrir convocatoria' })).getByRole('button', { name: 'Abrir convocatoria' }))

    await waitFor(() => expect(convocatoriasInteres.abrir).toHaveBeenCalledWith(1))
    expect(await screen.findByText('Se abrió la convocatoria 2026-2027.')).toBeInTheDocument()
  })

  it('una cerrada no se edita ni se elimina', async () => {
    await abrir()

    expect(screen.queryByRole('button', { name: 'Editar la convocatoria 2025-2026' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Eliminar la convocatoria 2025-2026' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Eliminar la convocatoria 2026-2027' })).toBeInTheDocument()
  })

  it('valida el año académico', async () => {
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) convocatoria/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Año académico/), { target: { value: '2026-2028' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await within(dialogo).findByText(/dos años consecutivos/)).toBeInTheDocument()
  })

  it('un rol local no gestiona convocatorias', async () => {
    await abrir(ADMIN_LOCAL)

    expect(screen.queryByRole('button', { name: /Nuevo\(a\) convocatoria/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Abrir la convocatoria/ })).not.toBeInTheDocument()
  })
})

describe('oferta', () => {
  it('un rol local agrega carreras sin elegir entidad y no quita las de la CI', async () => {
    ofertas.crear.mockResolvedValue({ ...OFERTA_PROPIA, id: 9 })
    await abrir(ADMIN_LOCAL)
    fireEvent.click(screen.getByRole('tab', { name: 'Oferta de carreras' }))

    await screen.findByText('Contabilidad')
    expect(screen.queryByRole('button', { name: 'Eliminar Derecho' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Eliminar Contabilidad' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Agregar carrera' }))
    const dialogo = screen.getByRole('dialog', { name: 'Agregar carrera' })
    expect(within(dialogo).queryByLabelText(/Facultad o CUM/)).not.toBeInTheDocument()
    await within(dialogo).findByRole('option', { name: 'Derecho' })
    fireEvent.change(within(dialogo).getByLabelText(/^Carrera/), { target: { value: '4' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(ofertas.crear).toHaveBeenCalledWith({ convocatoria: 1, carrera: '4' }))
    expect(ofertas.listar).toHaveBeenCalledWith(expect.objectContaining({ convocatoria: 1 }))
  })

  it('la CI elige la entidad', async () => {
    ofertas.crear.mockResolvedValue({ ...OFERTA_CI, id: 9 })
    await abrir()
    fireEvent.click(screen.getByRole('tab', { name: 'Oferta de carreras' }))

    fireEvent.click(await screen.findByRole('button', { name: 'Agregar carrera' }))
    const dialogo = screen.getByRole('dialog')
    await within(dialogo).findAllByRole('option', { name: 'Derecho' })
    fireEvent.change(within(dialogo).getByLabelText(/^Carrera/), { target: { value: '4' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Facultad o CUM/), { target: { value: 'cum_fum:4' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(ofertas.crear).toHaveBeenCalledWith({ convocatoria: 1, carrera: '4', cum_fum: '4' }))
  })
})

describe('interesados', () => {
  it('exporta a Excel con los filtros aplicados', async () => {
    expresiones.exportar.mockResolvedValue(new Blob(['x']))
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    const clic = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    await abrir()
    fireEvent.click(screen.getByRole('tab', { name: 'Interesados' }))

    expect(await screen.findByText('98042512345')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'mar' } })
    fireEvent.click(screen.getByRole('button', { name: 'Exportar Excel' }))

    await waitFor(() => expect(expresiones.exportar).toHaveBeenCalledWith({ convocatoria: 1, buscar: 'mar' }))
    expect(clic).toHaveBeenCalled()
  })
})
