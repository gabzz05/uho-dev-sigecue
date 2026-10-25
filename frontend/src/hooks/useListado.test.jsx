import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useListado } from './useListado'

function recursoFalso() {
  return {
    ruta: '/x/',
    listar: vi.fn().mockResolvedValue({ count: 45, results: [{ id: 1, nombre: 'Uno' }] }),
  }
}

afterEach(() => vi.useRealTimers())

describe('useListado', () => {
  it('carga la primera página sin filtros vacíos', async () => {
    const recurso = recursoFalso()
    const { result } = renderHook(() => useListado(recurso, { filtrosIniciales: { buscar: '', activo: '' } }))

    await waitFor(() => expect(result.current.cargando).toBe(false))
    expect(result.current.filas).toEqual([{ id: 1, nombre: 'Uno' }])
    expect(result.current.total).toBe(45)
    expect(recurso.listar).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('cambiar un filtro vuelve a la página 1', async () => {
    const recurso = recursoFalso()
    const { result } = renderHook(() => useListado(recurso))
    await waitFor(() => expect(result.current.cargando).toBe(false))

    act(() => result.current.setPagina(3))
    await waitFor(() => expect(recurso.listar).toHaveBeenLastCalledWith({ page: 3, page_size: 20 }))
    act(() => result.current.cambiarFiltro('activo', 'true'))

    await waitFor(() => expect(recurso.listar).toHaveBeenLastCalledWith({ activo: 'true', page: 1, page_size: 20 }))
  })

  it('la búsqueda espera a que el usuario deje de escribir', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const recurso = recursoFalso()
    const { result } = renderHook(() => useListado(recurso, { filtrosIniciales: { buscar: '' } }))
    await waitFor(() => expect(recurso.listar).toHaveBeenCalledTimes(1))

    act(() => result.current.cambiarFiltro('buscar', 'i'))
    act(() => result.current.cambiarFiltro('buscar', 'inf'))
    act(() => vi.advanceTimersByTime(350))

    await waitFor(() => expect(recurso.listar).toHaveBeenLastCalledWith({ buscar: 'inf', page: 1, page_size: 20 }))
    expect(recurso.listar.mock.calls.some(([p]) => p.buscar === 'i')).toBe(false)
  })

  it('expone el error de la API', async () => {
    const recurso = { ruta: '/x/', listar: vi.fn().mockRejectedValue({ response: { data: { error: { mensaje: 'Sin permiso' } } } }) }
    const { result } = renderHook(() => useListado(recurso))

    await waitFor(() => expect(result.current.error).toBe('Sin permiso'))
  })

  it('recargar vuelve a pedir los datos', async () => {
    const recurso = recursoFalso()
    const { result } = renderHook(() => useListado(recurso))
    await waitFor(() => expect(result.current.cargando).toBe(false))

    act(() => result.current.recargar())

    await waitFor(() => expect(recurso.listar).toHaveBeenCalledTimes(2))
  })
})
