import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as aspirante from '../../services/aspirante'
import * as auth from '../../services/auth'
import { publico } from '../../services/publico'
import { ASPIRANTE, renderApp } from '../../test/renderApp'

vi.mock('../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../services/aspirante', () => ({
  perfilAspirante: { obtener: vi.fn(), actualizar: vi.fn(), subirDocumento: vi.fn() },
  solicitudes: { listar: vi.fn(), crear: vi.fn(), guardarCarreras: vi.fn(), confirmar: vi.fn(), ofertas: vi.fn() },
  obtenerArchivo: vi.fn(),
  tiposDocumento: {},
}))
vi.mock('../../services/publico', async (importOriginal) => {
  const { publico: real } = await importOriginal()
  return { publico: { ...real, convocatoriaSolicitud: vi.fn() } }
})

const { perfilAspirante, solicitudes } = aspirante

const REQUISITOS = ['datos_personales', 'correo_validado', 'privacidad', 'foto', 'centro_trabajo', 'indice', 'documentos', 'carreras']

function perfil({ listo = true, faltan = [], ...extra } = {}) {
  return {
    nombre: 'María', apellidos: 'González', ci: '98042512345', email: 'maria@nauta.cu', celular: '55123456', tiene_foto: listo,
    centro_trabajo: listo ? 'Empresa Eléctrica' : '', indice_declarado: listo ? 92.5 : null, indice_validado: null,
    perfil_completo: false, bloqueado: false,
    requisitos: REQUISITOS.map((clave) => ({ clave, nombre: clave, cumple: listo && !faltan.includes(clave) })),
    documentos: [
      { tipo: { id: 1, nombre: 'CI anverso', obligatorio: true }, documento: listo ? DOCUMENTO : null },
      { tipo: { id: 3, nombre: 'Certificación de estudios', obligatorio: true }, documento: null },
    ],
    limites: { listo_para_carreras: listo, cuota_usada: 0, cuota_maxima: 20971520, archivo_maximo: 5242880, versiones_maximas: 10 },
    ...extra,
  }
}

const DOCUMENTO = { id: 7, version: 1, nombre_original: 'ci.pdf', formato: 'PDF', tamano: 2048, subido_at: '2026-10-20T10:00:00Z', archivo: '/documentos/7/archivo/' }

function oferta(id, carrera, carrera_nombre, tipo_entidad, entidad_nombre) {
  return { id, carrera, carrera_nombre, duracion_anios: 5, tipo_entidad, entidad_nombre, municipio: 'Holguín', plazas: 10 }
}

const OFERTAS = [
  oferta(10, 1, 'Ingeniería Informática', 'facultad', 'Facultad de Informática'),
  oferta(11, 1, 'Ingeniería Informática', 'cum_fum', 'CUM Banes'),
  oferta(12, 1, 'Ingeniería Informática', 'cum_fum', 'CUM Antilla'),
  oferta(13, 2, 'Derecho', 'cum_fum', 'CUM Banes'),
]

function solicitud({ estado = 'borrador', carreras = [], ...extra } = {}) {
  return {
    id: 5, estado, editable: true, created_at: '2026-10-20T10:00:00Z', confirmada_at: null, modificada_at: null, max_carreras: 5,
    convocatoria: { id: 1, anio_academico: '2026-2027', numero: 1, fecha_inicio: '2026-10-01', fecha_cierre: '2026-11-30', acepta_solicitudes: true },
    carreras: carreras.map((o, i) => ({ prioridad: i + 1, estado: 'pendiente', estado_nombre: 'Pendiente', oferta: o })),
    ...extra,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue({ ...ASPIRANTE, foto: null })
  perfilAspirante.obtener.mockResolvedValue(perfil())
  solicitudes.listar.mockResolvedValue([])
  solicitudes.ofertas.mockResolvedValue(OFERTAS)
  publico.convocatoriaSolicitud.mockResolvedValue({ anio_academico: '2026-2027', numero: 1, fecha_cierre: '2026-11-30' })
})

describe('inicio del aspirante', () => {
  it('con el perfil incompleto marca ese paso y lleva a completarlo', async () => {
    perfilAspirante.obtener.mockResolvedValue(perfil({ listo: false }))
    renderApp('/aspirante')

    expect(await screen.findByRole('heading', { name: 'Hola, María González' })).toBeInTheDocument()
    expect(screen.getByText('Completar perfil', { selector: 'li span' }).closest('li')).toHaveAttribute('aria-current', 'step')
    expect(screen.getByRole('link', { name: 'Completar perfil' })).toHaveAttribute('href', '/aspirante/completar-perfil')
    expect(screen.getByText('Convocatoria activa')).toBeInTheDocument()
  })

  it('muestra el estado de la solicitud', async () => {
    solicitudes.listar.mockResolvedValue([solicitud({ estado: 'pendiente', carreras: [OFERTAS[0]] })])
    renderApp('/aspirante')

    expect(await screen.findByText('Ingeniería Informática')).toBeInTheDocument()
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver y editar mi solicitud' })).toBeInTheDocument()
  })
})

describe('completar perfil', () => {
  it('valida el índice y guarda los datos', async () => {
    perfilAspirante.obtener.mockResolvedValue(perfil({ listo: false }))
    perfilAspirante.actualizar.mockResolvedValue(perfil({ listo: false, centro_trabajo: 'ETECSA' }))
    renderApp('/aspirante/completar-perfil')

    fireEvent.change(await screen.findByLabelText(/^Centro de trabajo actual/), { target: { value: 'ETECSA' } })
    fireEvent.change(screen.getByLabelText(/^Índice académico/), { target: { value: '120' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar datos' }))
    expect(await screen.findByText('Escribe un número entre 0 y 100.')).toBeInTheDocument()
    expect(perfilAspirante.actualizar).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText(/^Índice académico/), { target: { value: '91.5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar datos' }))
    await waitFor(() => expect(perfilAspirante.actualizar).toHaveBeenCalledWith({ centro_trabajo: 'ETECSA', indice_declarado: 91.5 }))
  })

  it('sube un documento y muestra lo que falta', async () => {
    perfilAspirante.subirDocumento.mockResolvedValue(perfil())
    renderApp('/aspirante/completar-perfil')

    expect(await screen.findByRole('button', { name: 'Sustituir CI anverso' })).toBeInTheDocument()
    expect(screen.getByText('Sin subir')).toBeInTheDocument()
    const archivo = new File(['%PDF-1.4'], 'cert.pdf', { type: 'application/pdf' })
    const entrada = screen.getByRole('button', { name: 'Subir Certificación de estudios' }).parentElement.querySelector('input[type=file]')
    fireEvent.change(entrada, { target: { files: [archivo] } })

    await waitFor(() => expect(perfilAspirante.subirDocumento).toHaveBeenCalledWith(3, archivo))
  })

  it('rechaza en el navegador archivos de más de 5 MB', async () => {
    renderApp('/aspirante/completar-perfil')

    const grande = new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'cert.pdf', { type: 'application/pdf' })
    const entrada = (await screen.findByRole('button', { name: 'Subir Certificación de estudios' })).parentElement.querySelector('input[type=file]')
    fireEvent.change(entrada, { target: { files: [grande] } })

    expect(await screen.findByRole('alert')).toHaveTextContent('no puede superar 5 MB')
    expect(perfilAspirante.subirDocumento).not.toHaveBeenCalled()
  })

  it('congelado, solo lectura', async () => {
    perfilAspirante.obtener.mockResolvedValue(perfil({ bloqueado: true }))
    renderApp('/aspirante/completar-perfil')

    expect(await screen.findByText('Perfil congelado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar datos' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Sustituir/ })).not.toBeInTheDocument()
  })
})

describe('mi solicitud', () => {
  async function abrir(datos) {
    solicitudes.listar.mockResolvedValue([datos])
    renderApp('/aspirante/solicitud')
    await screen.findByText(/Carreras seleccionadas/)
  }

  it('sin perfil listo pide completarlo', async () => {
    perfilAspirante.obtener.mockResolvedValue(perfil({ listo: false }))
    renderApp('/aspirante/solicitud')

    expect(await screen.findByText('Completa tu perfil primero')).toBeInTheDocument()
  })

  it('crea la solicitud si no tiene', async () => {
    solicitudes.crear.mockResolvedValue(solicitud())
    renderApp('/aspirante/solicitud')

    fireEvent.click(await screen.findByRole('button', { name: 'Nueva solicitud' }))

    expect(await screen.findByText('Carreras seleccionadas (0 de 5)')).toBeInTheDocument()
  })

  it('agrega carreras respetando RF-049 y guarda el orden', async () => {
    solicitudes.guardarCarreras.mockResolvedValue(solicitud({ carreras: [OFERTAS[1], OFERTAS[0]] }))
    await abrir(solicitud())

    fireEvent.click(screen.getByRole('button', { name: 'Agregar carrera' }))
    const catalogo = screen.getByRole('dialog', { name: 'Agregar carrera' })
    fireEvent.click(within(catalogo).getByRole('button', { name: 'Agregar Ingeniería Informática en Facultad de Informática' }))
    fireEvent.click(within(catalogo).getByRole('button', { name: 'Agregar Ingeniería Informática en CUM Banes' }))

    // Ya tiene Informática en un CUM: no puede elegirla en otro.
    expect(within(catalogo).getByRole('button', { name: 'Agregar Ingeniería Informática en CUM Antilla' })).toBeDisabled()
    expect(within(catalogo).getByText('Ya la elegiste en CUM Banes')).toBeInTheDocument()
    fireEvent.keyDown(catalogo, { key: 'Escape' })

    fireEvent.click(screen.getByRole('button', { name: 'Bajar Ingeniería Informática en Facultad de Informática' }))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => expect(solicitudes.guardarCarreras).toHaveBeenCalledWith(5, [11, 10]))
  })

  it('reordena con el teclado sobre el asa', async () => {
    await abrir(solicitud({ carreras: [OFERTAS[0], OFERTAS[3]] }))

    const asa = screen.getByRole('button', { name: /^Mover Derecho en CUM Banes/ })
    fireEvent.keyDown(asa, { key: 'ArrowUp' })

    const filas = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(filas[0]).toContain('Derecho')
    expect(screen.getByText('Derecho en CUM Banes: ahora en la posición 1 de 2.')).toBeInTheDocument()
    expect(screen.getByText('Tienes cambios sin guardar.')).toBeInTheDocument()
  })

  it('confirma un borrador guardado', async () => {
    solicitudes.confirmar.mockResolvedValue(solicitud({ estado: 'pendiente', carreras: [OFERTAS[0]], confirmada_at: '2026-10-21T10:00:00Z' }))
    await abrir(solicitud({ carreras: [OFERTAS[0]] }))

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar solicitud' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Confirmar solicitud' })).getByRole('button', { name: 'Confirmar solicitud' }))

    await waitFor(() => expect(solicitudes.confirmar).toHaveBeenCalledWith(5))
    expect(await screen.findByText('Pendiente')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar solicitud' })).not.toBeInTheDocument()
  })

  it('con la convocatoria cerrada es de solo lectura', async () => {
    solicitudes.ofertas.mockResolvedValue([])
    const cerrada = solicitud({ estado: 'pendiente', editable: false, carreras: [OFERTAS[0]] })
    await abrir({ ...cerrada, convocatoria: { ...cerrada.convocatoria, acepta_solicitudes: false } })

    expect(screen.queryByRole('button', { name: 'Agregar carrera' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Mover/ })).not.toBeInTheDocument()
    expect(screen.getByText(/esta es la versión que se tendrá en cuenta/)).toBeInTheDocument()
  })
})
