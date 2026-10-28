import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../services/auth'
import { publico } from '../../services/publico'
import { renderApp } from '../../test/renderApp'

vi.mock('../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../services/publico', async (importOriginal) => {
  const { publico: real } = await importOriginal()
  return {
    publico: {
      ...real,
      resultados: { ruta: '/publico/resultados/', listar: vi.fn() },
      filtrosResultados: vi.fn(),
      consultarResultado: vi.fn(),
    },
  }
})

const FILTROS = {
  convocatorias: [{ id: 3, nombre: '1.ª convocatoria 2026-2027' }, { id: 4, nombre: '2.ª convocatoria 2026-2027' }],
  carreras: ['Derecho', 'Ingeniería Informática'],
  entidades: ['CUM Banes', 'Facultad de Informática'],
}
const FILA = { nombre: 'Ana Pérez', ci: '*******2341', carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática', convocatoria: '2.ª convocatoria 2026-2027' }

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue(null)
  publico.filtrosResultados.mockResolvedValue(FILTROS)
  publico.resultados.listar.mockResolvedValue({ count: 1, results: [FILA] })
})

describe('resultados públicos', () => {
  it('muestra el listado de la convocatoria más reciente, sin descarga', async () => {
    renderApp('/resultados')

    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('*******2341')).toBeInTheDocument()
    expect(publico.resultados.listar).toHaveBeenCalledWith(expect.objectContaining({ otorgamiento: '4' }))
    expect(screen.queryByRole('button', { name: /Excel|PDF|Descargar/ })).not.toBeInTheDocument()
  })

  it('filtra por carrera', async () => {
    renderApp('/resultados')
    await screen.findByText('Ana Pérez')

    fireEvent.change(screen.getByLabelText('Carrera'), { target: { value: 'Derecho' } })

    await waitFor(() => expect(publico.resultados.listar).toHaveBeenLastCalledWith(expect.objectContaining({ carrera: 'Derecho' })))
  })

  it('consulta el resultado propio por CI', async () => {
    publico.consultarResultado.mockResolvedValue({
      resultados: [{ convocatoria: '1.ª convocatoria 2026-2027', resultado: 'No seleccionado', carrera: null, entidad: null }],
    })
    renderApp('/resultados')

    fireEvent.change(await screen.findByLabelText('Carnet de identidad'), { target: { value: '90010112341' } })
    fireEvent.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByText('1.ª convocatoria 2026-2027: No seleccionado')).toBeInTheDocument()
    expect(publico.consultarResultado).toHaveBeenCalledWith('90010112341')
  })

  it('valida el CI antes de consultar y muestra el mensaje genérico de la API', async () => {
    publico.consultarResultado.mockRejectedValue({ response: { data: { error: { mensaje: 'No existe un resultado publicado para los datos introducidos.' } } } })
    renderApp('/resultados')

    fireEvent.change(await screen.findByLabelText('Carnet de identidad'), { target: { value: '123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Consultar' }))
    expect(await screen.findByText('Escribe los 11 dígitos de tu carnet de identidad.')).toBeInTheDocument()
    expect(publico.consultarResultado).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Carnet de identidad'), { target: { value: '11111111111' } })
    fireEvent.click(screen.getByRole('button', { name: 'Consultar' }))
    expect(await screen.findByText('No existe un resultado publicado para los datos introducidos.')).toBeInTheDocument()
  })

  it('sin resultados publicados lo indica', async () => {
    publico.filtrosResultados.mockResolvedValue({ convocatorias: [], carreras: [], entidades: [] })
    renderApp('/resultados')

    expect(await screen.findByText('No hay resultados publicados')).toBeInTheDocument()
  })
})
