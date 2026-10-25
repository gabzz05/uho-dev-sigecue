import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'
import { crearRecurso, omitirArchivoSinCambios } from './recursos'

vi.mock('./api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }))

beforeEach(() => vi.clearAllMocks())

describe('crearRecurso', () => {
  const carreras = crearRecurso('/admin/nomencladores/carreras/')

  it('lista con parámetros y devuelve el cuerpo', async () => {
    api.get.mockResolvedValue({ data: { count: 0, results: [] } })

    await expect(carreras.listar({ page: 2 })).resolves.toEqual({ count: 0, results: [] })
    expect(api.get).toHaveBeenCalledWith('/admin/nomencladores/carreras/', { params: { page: 2 } })
  })

  it('envía JSON si no hay archivos', async () => {
    api.post.mockResolvedValue({ data: {} })

    await carreras.crear({ nombre: 'Derecho' })

    expect(api.post).toHaveBeenCalledWith('/admin/nomencladores/carreras/', { nombre: 'Derecho' })
  })

  it('envía multipart si hay un archivo', async () => {
    api.patch.mockResolvedValue({ data: {} })
    const archivo = new File(['x'], 'foto.png', { type: 'image/png' })

    await carreras.actualizar(3, { nombre: 'Derecho', imagen: archivo, descripcion: null })

    const [url, cuerpo] = api.patch.mock.calls[0]
    expect(url).toBe('/admin/nomencladores/carreras/3/')
    expect(cuerpo).toBeInstanceOf(FormData)
    expect(cuerpo.get('imagen')).toBe(archivo)
    expect(cuerpo.get('descripcion')).toBe('')
  })

  it('elimina por id', async () => {
    await carreras.eliminar(7)
    expect(api.delete).toHaveBeenCalledWith('/admin/nomencladores/carreras/7/')
  })
})

describe('omitirArchivoSinCambios', () => {
  it('no reenvía la URL de una imagen ya guardada', () => {
    expect(omitirArchivoSinCambios({ nombre: 'X', imagen: 'http://x/media/a.png' })).toEqual({ nombre: 'X' })
  })

  it('conserva un archivo nuevo o la orden de quitarlo', () => {
    const archivo = new File(['x'], 'a.png')
    expect(omitirArchivoSinCambios({ imagen: archivo }).imagen).toBe(archivo)
    expect(omitirArchivoSinCambios({ imagen: '' })).toEqual({ imagen: '' })
  })
})
