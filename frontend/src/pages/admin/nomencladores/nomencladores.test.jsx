import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import * as nomencladores from '../../../services/nomencladores'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({
  restaurarSesion: vi.fn(),
  iniciarSesion: vi.fn(),
  cerrarSesion: vi.fn(),
}))

vi.mock('../../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn() })
  return {
    municipios: recurso('municipios'),
    facultades: recurso('facultades'),
    cumFum: recurso('cum-fum'),
    areas: recurso('areas'),
    departamentos: recurso('departamentos'),
    cargos: recurso('cargos'),
    carreras: recurso('carreras'),
  }
})

const pagina = (results) => ({ count: results.length, results })

const INFORMATICA = {
  id: 1, nombre: 'Ingeniería Informática', codigo: 'II', duracion_anios: 5,
  modalidad_nombre: 'Por encuentro', activo: true, imagen: null,
}

const JEFE_CI = perfil({ permisos: ['nomencladores.ver', 'nomencladores.crear', 'nomencladores.editar', 'nomencladores.eliminar'] })
const ADMIN_LOCAL = perfil({
  username: 'admin_fac',
  rol: { codigo: 'admin_facultad', nombre: 'Admin Facultad', ambito: 'facultad' },
  permisos: ['nomencladores.ver', 'nomencladores.crear', 'nomencladores.editar'],
})

beforeEach(() => {
  vi.clearAllMocks()
  Object.values(nomencladores).forEach((r) => r.listar.mockResolvedValue(pagina([])))
  nomencladores.carreras.listar.mockResolvedValue(pagina([INFORMATICA]))
})

async function abrir(ruta, usuario = JEFE_CI) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp(ruta)
}

describe('Carreras', () => {
  it('lista las carreras con su estado', async () => {
    await abrir('/admin/carreras')

    const fila = (await screen.findByText('Ingeniería Informática')).closest('tr')
    expect(within(fila).getByText('5 años')).toBeInTheDocument()
    expect(within(fila).getByText('Activo')).toBeInTheDocument()
  })

  it('un rol local ve el catálogo pero no puede modificarlo', async () => {
    await abrir('/admin/carreras', ADMIN_LOCAL)

    await screen.findByText('Ingeniería Informática')
    expect(screen.queryByRole('button', { name: /Nuevo\(a\) carrera/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Editar/ })).not.toBeInTheDocument()
  })

  it('crea una carrera validando antes de enviar', async () => {
    nomencladores.carreras.crear.mockResolvedValue({ id: 2, nombre: 'Derecho' })
    await abrir('/admin/carreras')

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo\(a\) carrera/ }))
    const dialogo = screen.getByRole('dialog', { name: 'Nuevo(a) carrera' })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    expect(await within(dialogo).findByText('Escribe el nombre de la carrera.')).toBeInTheDocument()
    expect(nomencladores.carreras.crear).not.toHaveBeenCalled()

    fireEvent.change(within(dialogo).getByLabelText(/^Nombre/), { target: { value: 'Derecho' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Código/), { target: { value: 'DER' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Duración/), { target: { value: '5' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Se creó: Derecho.')).toBeInTheDocument()
    expect(nomencladores.carreras.crear).toHaveBeenCalledWith(expect.objectContaining({ nombre: 'Derecho', codigo: 'DER' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(nomencladores.carreras.listar).toHaveBeenCalledTimes(2))
  })

  it('muestra los errores por campo de la API', async () => {
    nomencladores.carreras.crear.mockRejectedValue({
      response: { data: { error: { mensaje: 'Revisa los datos', detalles: { codigo: ['Ya existe una carrera con este código.'] } } } },
    })
    await abrir('/admin/carreras')

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo\(a\) carrera/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Nombre/), { target: { value: 'Derecho' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Código/), { target: { value: 'II' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Duración/), { target: { value: '5' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await within(dialogo).findByText('Ya existe una carrera con este código.')).toBeInTheDocument()
  })

  it('al editar no reenvía la imagen que no cambió', async () => {
    nomencladores.carreras.listar.mockResolvedValue(pagina([{ ...INFORMATICA, imagen: 'http://x/media/carreras/a.png' }]))
    nomencladores.carreras.actualizar.mockResolvedValue({ ...INFORMATICA })
    await abrir('/admin/carreras')

    fireEvent.click(await screen.findByRole('button', { name: 'Editar Ingeniería Informática' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(nomencladores.carreras.actualizar).toHaveBeenCalled())
    expect(nomencladores.carreras.actualizar.mock.calls[0][1]).not.toHaveProperty('imagen')
  })

  it('desactiva una carrera', async () => {
    nomencladores.carreras.actualizar.mockResolvedValue({})
    await abrir('/admin/carreras')

    fireEvent.click(await screen.findByRole('button', { name: 'Desactivar Ingeniería Informática' }))

    await waitFor(() => expect(nomencladores.carreras.actualizar).toHaveBeenCalledWith(1, { activo: false }))
  })

  it('pide confirmación para eliminar e informa si está en uso', async () => {
    nomencladores.carreras.eliminar.mockRejectedValue({
      response: { data: { error: { mensaje: 'Este registro está en uso y no se puede eliminar. Puedes desactivarlo.' } } },
    })
    await abrir('/admin/carreras')

    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar Ingeniería Informática' }))
    const confirmacion = screen.getByRole('dialog', { name: 'Eliminar carrera' })
    fireEvent.click(within(confirmacion).getByRole('button', { name: 'Eliminar' }))

    expect(await screen.findByText(/Este registro está en uso/)).toBeInTheDocument()
    expect(nomencladores.carreras.eliminar).toHaveBeenCalledWith(1)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('Áreas', () => {
  it('un rol global elige la entidad y se envía como facultad o cum_fum', async () => {
    nomencladores.facultades.listar.mockResolvedValue(pagina([{ id: 3, nombre: 'Fac. Informática' }]))
    nomencladores.areas.crear.mockResolvedValue({ id: 1, nombre: 'Software' })
    await abrir('/admin/nomencladores')

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo\(a\) área/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Nombre/), { target: { value: 'Software' } })
    await within(dialogo).findByRole('option', { name: 'Fac. Informática' })
    fireEvent.change(within(dialogo).getByLabelText(/^Facultad o CUM/), { target: { value: 'facultad:3' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() =>
      expect(nomencladores.areas.crear).toHaveBeenCalledWith({ nombre: 'Software', facultad: '3', cum_fum: null }),
    )
  })

  it('un rol local crea áreas sin elegir entidad', async () => {
    nomencladores.areas.crear.mockResolvedValue({ id: 1, nombre: 'Software' })
    await abrir('/admin/nomencladores', ADMIN_LOCAL)

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo\(a\) área/ }))
    const dialogo = screen.getByRole('dialog')
    expect(within(dialogo).queryByLabelText(/Facultad o CUM/)).not.toBeInTheDocument()
    fireEvent.change(within(dialogo).getByLabelText(/^Nombre/), { target: { value: 'Software' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(nomencladores.areas.crear).toHaveBeenCalledWith({ nombre: 'Software' }))
  })

  it('las pestañas se recorren con las flechas', async () => {
    await abrir('/admin/nomencladores')

    const areas = await screen.findByRole('tab', { name: 'Áreas' })
    fireEvent.keyDown(areas, { key: 'ArrowRight' })

    expect(screen.getByRole('tab', { name: 'Departamentos' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Departamentos' }), { key: 'ArrowLeft' })
    expect(screen.getByRole('tab', { name: 'Áreas' })).toHaveAttribute('aria-selected', 'true')
  })
})

describe('Entidades', () => {
  it('muestra facultades y CUM/FUM en pestañas', async () => {
    nomencladores.facultades.listar.mockResolvedValue(pagina([{ id: 1, nombre: 'Fac. Informática', codigo: 'FI', municipio_nombre: 'Holguín', activo: true }]))
    nomencladores.cumFum.listar.mockResolvedValue(pagina([{ id: 2, nombre: 'CUM Moa', codigo: 'CM', tipo: 'CUM', municipio_nombre: 'Moa', activo: true }]))
    await abrir('/admin/entidades')

    expect(await screen.findByText('Fac. Informática')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'CUM / FUM' }))
    expect(await screen.findByText('CUM Moa')).toBeInTheDocument()
  })
})
