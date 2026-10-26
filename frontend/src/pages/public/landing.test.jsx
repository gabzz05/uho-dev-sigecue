import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../services/auth'
import { publico } from '../../services/publico'
import { renderApp } from '../../test/renderApp'

vi.mock('../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../services/publico', () => ({
  publico: {
    convocatoriaInteres: vi.fn(),
    convocatoriaSolicitud: vi.fn(),
    filtros: vi.fn(),
    carrera: vi.fn(),
    registrarInteres: vi.fn(),
    oferta: { ruta: '/oferta/', listar: vi.fn() },
    carreras: { ruta: '/carreras/', listar: vi.fn() },
  },
}))

const pagina = (results) => ({ count: results.length, results })
const INFORMATICA = { id: 1, nombre: 'Ingeniería Informática', duracion_anios: 5, descripcion: 'Desarrollo de software.', imagen: null }
const ENTIDAD = { tipo: 'facultad', id: 3, nombre: 'Facultad de Informática', municipio: 'Holguín' }
const OFERTA = { id: 10, carrera: INFORMATICA, entidad: ENTIDAD, anio_academico: '2026-2027' }
const CONVOCATORIA = { anio_academico: '2026-2027', fecha_inicio: '2026-10-01', fecha_cierre: '2026-12-15', mensaje_publico: '¡Participa!' }

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue(null)
  publico.convocatoriaSolicitud.mockResolvedValue(null)
  publico.filtros.mockResolvedValue({ facultades: [{ id: 3, nombre: 'Facultad de Informática' }], cum_fum: [{ id: 5, nombre: 'CUM Moa', tipo: 'CUM' }], municipios: [{ id: 1, nombre: 'Holguín' }] })
  publico.oferta.listar.mockResolvedValue(pagina([OFERTA]))
  publico.carreras.listar.mockResolvedValue(pagina([INFORMATICA]))
})

describe('landing sin convocatoria abierta', () => {
  beforeEach(() => publico.convocatoriaInteres.mockResolvedValue(null))

  it('muestra el catálogo sin "Me interesa" ni filtros de entidad', async () => {
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Ingeniería Informática' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Me interesa/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Facultad / CUM')).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: /Convocatoria de interés abierta/ })).not.toBeInTheDocument()
    expect(publico.oferta.listar).not.toHaveBeenCalled()
  })

  it('incluye la sección institucional', async () => {
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Misión' })).toBeInTheDocument()
  })
})

describe('landing con convocatoria abierta', () => {
  beforeEach(() => publico.convocatoriaInteres.mockResolvedValue(CONVOCATORIA))

  it('muestra el aviso y la oferta con su entidad, sin contador de interesados', async () => {
    renderApp('/')

    const aviso = await screen.findByRole('region', { name: 'Convocatoria de interés abierta' })
    expect(aviso).toHaveTextContent('hasta el 15/12/2026')
    expect(aviso).toHaveTextContent('¡Participa!')
    const tarjeta = (await screen.findByRole('heading', { name: 'Ingeniería Informática' })).closest('article')
    expect(within(tarjeta).getByText('Facultad de Informática')).toBeInTheDocument()
    expect(within(tarjeta).getByText(/Holguín/)).toBeInTheDocument()
    expect(screen.queryByText(/interesados/i)).not.toBeInTheDocument()
  })

  it('filtra por entidad enviando facultad o cum_fum', async () => {
    renderApp('/')
    await screen.findByRole('option', { name: 'CUM Moa' })

    fireEvent.change(screen.getByLabelText('Facultad / CUM'), { target: { value: 'cum_fum:5' } })

    await waitFor(() => expect(publico.oferta.listar).toHaveBeenLastCalledWith({ cum_fum: '5', page: 1, page_size: 12 }))
  })

  it('registra el interés validando antes de enviar', async () => {
    publico.registrarInteres.mockResolvedValue({ mensaje: 'Registramos tu interés.' })
    renderApp('/')

    fireEvent.click(await screen.findByRole('button', { name: /Me interesa/ }))
    const dialogo = screen.getByRole('dialog', { name: 'Ingeniería Informática' })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Registrar interés' }))
    expect(await within(dialogo).findByText('Escribe tu nombre y apellidos.')).toBeInTheDocument()

    fireEvent.change(within(dialogo).getByLabelText(/Nombre completo/), { target: { value: 'María González' } })
    fireEvent.change(within(dialogo).getByLabelText(/Carnet de identidad/), { target: { value: '98042512345' } })
    fireEvent.change(within(dialogo).getByLabelText(/Celular/), { target: { value: '55123456' } })
    fireEvent.change(within(dialogo).getByLabelText(/Correo/), { target: { value: 'maria@nauta.cu' } })
    fireEvent.click(within(dialogo).getByLabelText(/Acepto que mis datos/))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Registrar interés' }))

    expect(await within(dialogo).findByText('Registramos tu interés.')).toBeInTheDocument()
    expect(publico.registrarInteres).toHaveBeenCalledWith({
      oferta: 10, nombre: 'María González', ci: '98042512345', celular: '55123456', email: 'maria@nauta.cu', acepta_privacidad: true,
    })
  })

  it('muestra el error de la API (p. ej. interés repetido)', async () => {
    publico.registrarInteres.mockRejectedValue({ response: { data: { error: { mensaje: 'Ya registraste tu interés en esta carrera para este año.' } } } })
    renderApp('/')

    fireEvent.click(await screen.findByRole('button', { name: /Me interesa/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/Nombre completo/), { target: { value: 'María González' } })
    fireEvent.change(within(dialogo).getByLabelText(/Carnet de identidad/), { target: { value: '98042512345' } })
    fireEvent.change(within(dialogo).getByLabelText(/Celular/), { target: { value: '55123456' } })
    fireEvent.change(within(dialogo).getByLabelText(/Correo/), { target: { value: 'maria@nauta.cu' } })
    fireEvent.click(within(dialogo).getByLabelText(/Acepto que mis datos/))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Registrar interés' }))

    expect(await within(dialogo).findByText('Ya registraste tu interés en esta carrera para este año.')).toBeInTheDocument()
  })
})

describe('aviso de la convocatoria de solicitud', () => {
  const SOLICITUD = { anio_academico: '2026-2027', numero: 1, fecha_inicio: '2026-11-01', fecha_cierre: '2026-11-30', mensaje_publico: '' }

  it('aparece antes que el de interés y lleva al registro', async () => {
    publico.convocatoriaInteres.mockResolvedValue(CONVOCATORIA)
    publico.convocatoriaSolicitud.mockResolvedValue(SOLICITUD)
    renderApp('/')

    const solicitud = await screen.findByRole('region', { name: 'Convocatoria de solicitud de matrícula abierta' })
    const interes = await screen.findByRole('region', { name: 'Convocatoria de interés abierta' })
    expect(solicitud.compareDocumentPosition(interes) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(solicitud).toHaveTextContent('del 01/11/2026 al 30/11/2026')
    expect(within(solicitud).getByRole('link', { name: 'Solicitar matrícula' })).toHaveAttribute('href', '/registro')
    expect(within(solicitud).getByRole('link', { name: 'Ya tengo cuenta' })).toHaveAttribute('href', '/login')
  })

  it('con sesión de aspirante lleva a su portal', async () => {
    publico.convocatoriaInteres.mockResolvedValue(null)
    publico.convocatoriaSolicitud.mockResolvedValue({ ...SOLICITUD, numero: 2 })
    auth.restaurarSesion.mockResolvedValue({ nombre: 'María', rol: { codigo: 'aspirante' }, permisos: [] })
    renderApp('/')

    const solicitud = await screen.findByRole('region', { name: 'Convocatoria de solicitud de matrícula abierta' })
    await waitFor(() => expect(within(solicitud).getByRole('link', { name: 'Solicitar matrícula' })).toHaveAttribute('href', '/aspirante'))
    expect(solicitud).toHaveTextContent('2.ª convocatoria')
    expect(within(solicitud).queryByRole('link', { name: 'Ya tengo cuenta' })).not.toBeInTheDocument()
  })
})

describe('detalle de carrera', () => {
  it('muestra la información y dónde se oferta', async () => {
    publico.convocatoriaInteres.mockResolvedValue(CONVOCATORIA)
    publico.carrera.mockResolvedValue({ ...INFORMATICA, objetivo: 'Formar ingenieros.', perfil_egresado: '', requisitos: '', ofertas: [OFERTA] })
    renderApp('/carreras/1')

    expect(await screen.findByRole('heading', { name: 'Ingeniería Informática', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Objetivo' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Requisitos de ingreso' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Me interesa en Facultad de Informática/ }))
    expect(screen.getByRole('dialog', { name: 'Ingeniería Informática' })).toBeInTheDocument()
    expect(publico.carrera).toHaveBeenCalledWith('1')
  })

  it('sin convocatoria lo indica', async () => {
    publico.convocatoriaInteres.mockResolvedValue(null)
    publico.carrera.mockResolvedValue({ ...INFORMATICA, ofertas: [] })
    renderApp('/carreras/1')

    expect(await screen.findByText(/no hay una convocatoria de interés abierta/)).toBeInTheDocument()
  })
})
