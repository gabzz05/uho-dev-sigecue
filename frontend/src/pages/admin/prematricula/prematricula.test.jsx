import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import { otorgamientos } from '../../../services/otorgamiento'
import { miPrematricula, prematriculasAdmin } from '../../../services/prematricula'
import { ASPIRANTE, perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/otorgamiento', () => ({ otorgamientos: { listar: vi.fn() } }))
vi.mock('../../../services/prematricula', () => ({
  miPrematricula: { listar: vi.fn(), obtener: vi.fn(), guardarTexto: vi.fn(), subirArchivo: vi.fn(), enviar: vi.fn() },
  prematriculasAdmin: {
    ruta: '/p/', listar: vi.fn(), obtener: vi.fn(), periodos: vi.fn(), opcionesFaltantes: vi.fn(), configurarPeriodo: vi.fn(),
    revisar: vi.fn(), solicitarCorrecciones: vi.fn(), aprobar: vi.fn(), exportarExcel: vi.fn(), exportarPdf: vi.fn(),
  },
  camposPrematricula: {},
}))

const OTORGAMIENTO = { id: 3, estado: 'publicado', convocatoria: { id: 1, anio_academico: '2026-2027', numero: 1 } }
const PERIODO = { id: 9, otorgamiento: 3, convocatoria: '1.ª convocatoria 2026-2027', fecha_inicio: '2026-11-01', fecha_cierre: '2026-11-20', abierto: true, cerrado: false }
const SECRETARIA = perfil({ rol: { codigo: 'secretaria_general', nombre: 'SG', ambito: 'global' }, permisos: ['prematricula.ver', 'prematricula.configurar'] })
const SEC_FAC = perfil({ rol: { codigo: 'secretario_facultad', nombre: 'Sec', ambito: 'facultad' }, permisos: ['prematricula.ver', 'prematricula.editar', 'solicitudes.documentos_descargar'] })

function elemento(id, nombre, extra = {}) {
  return {
    id, nombre, tipo: 'archivo', requerido: true, campo: id, tipo_documento: null, valor_texto: '', entregado: true,
    revision: 'pendiente', revision_nombre: 'Por revisar', observacion: '', revisado_at: null,
    archivo: { id, version: 1, nombre_original: `${id}.pdf`, formato: 'PDF', tamano: 1024, subido_at: '2026-11-02T10:00:00Z', archivo: `/prematricula/archivos/${id}/` },
    editable: true, ...extra,
  }
}

function expediente(extra = {}) {
  return {
    id: 5, estado: 'completada', estado_nombre: 'Completada', periodo: PERIODO, aspirante: 2, aspirante_nombre: 'Ana Pérez',
    carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática', faltantes: [], enviada_at: '2026-11-03T10:00:00Z',
    fecha_aprobacion: null, aprobado_por: null, updated_at: '2026-11-03T10:00:00Z',
    elementos: [elemento(1, 'CI anverso', { tipo: 'documento_perfil', campo: null, tipo_documento: 1, editable: false }), elemento(2, 'Foto tipo carné', { tipo: 'imagen' })],
    limites: { cuota_usada: 1024, cuota_maxima: 20971520 },
    permisos: { revisar: true, descargar: true, enviar: false },
    ...extra,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  otorgamientos.listar.mockResolvedValue([OTORGAMIENTO])
  prematriculasAdmin.periodos.mockResolvedValue([])
  prematriculasAdmin.opcionesFaltantes.mockResolvedValue([{ parametro: 'falta_campo', id: 2, nombre: 'Foto tipo carné' }])
  prematriculasAdmin.listar.mockResolvedValue({ count: 1, results: [expediente()] })
  prematriculasAdmin.obtener.mockResolvedValue(expediente())
})

describe('panel de prematrícula', () => {
  it('la Secretaría General abre el período', async () => {
    prematriculasAdmin.configurarPeriodo.mockResolvedValue(PERIODO)
    auth.restaurarSesion.mockResolvedValue(SECRETARIA)
    renderApp('/admin/prematricula')

    fireEvent.change(await screen.findByLabelText('Fecha de inicio'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Fecha de cierre'), { target: { value: '2026-11-20' } })
    fireEvent.click(screen.getByRole('button', { name: 'Abrir prematrícula' }))

    await waitFor(() => expect(prematriculasAdmin.configurarPeriodo).toHaveBeenCalledWith({ otorgamiento: 3, fecha_inicio: '2026-11-01', fecha_cierre: '2026-11-20' }))
    expect(await screen.findByText(/Del 01\/11\/2026 al 20\/11\/2026/)).toBeInTheDocument()
  })

  it('filtra por documento faltante', async () => {
    auth.restaurarSesion.mockResolvedValue(SEC_FAC)
    renderApp('/admin/prematricula')
    await screen.findByRole('link', { name: 'Ana Pérez' })

    fireEvent.change(screen.getByLabelText('Le falta'), { target: { value: 'falta_campo:2' } })

    await waitFor(() => expect(prematriculasAdmin.listar).toHaveBeenLastCalledWith(expect.objectContaining({ falta_campo: '2', otorgamiento: 3 })))
  })

  it('revisa por documento: aprueba, rechaza con observación y pide correcciones', async () => {
    prematriculasAdmin.revisar.mockResolvedValue(expediente())
    prematriculasAdmin.solicitarCorrecciones.mockResolvedValue(expediente({ estado: 'con_correcciones', permisos: { revisar: false, descargar: true, enviar: false } }))
    auth.restaurarSesion.mockResolvedValue(SEC_FAC)
    renderApp('/admin/prematricula/5')

    fireEvent.click(await screen.findByRole('button', { name: 'Aprobar CI anverso' }))
    await waitFor(() => expect(prematriculasAdmin.revisar).toHaveBeenCalledWith(5, 1, 'aprobado'))

    fireEvent.click(screen.getByRole('button', { name: 'Rechazar Foto tipo carné' }))
    const dialogo = screen.getByRole('dialog', { name: 'Rechazar: Foto tipo carné' })
    expect(within(dialogo).getByRole('button', { name: 'Rechazar' })).toBeDisabled()
    fireEvent.change(within(dialogo).getByLabelText(/^Observación/), { target: { value: 'Fondo no blanco' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Rechazar' }))
    await waitFor(() => expect(prematriculasAdmin.revisar).toHaveBeenCalledWith(5, 2, 'rechazado', 'Fondo no blanco'))

    fireEvent.click(screen.getByRole('button', { name: 'Solicitar correcciones' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Solicitar correcciones' })).getByRole('button', { name: 'Solicitar correcciones' }))
    await waitFor(() => expect(prematriculasAdmin.solicitarCorrecciones).toHaveBeenCalledWith(5))
    expect(await screen.findByText('Con correcciones')).toBeInTheDocument()
  })
})

describe('prematrícula del aspirante', () => {
  beforeEach(() => auth.restaurarSesion.mockResolvedValue({ ...ASPIRANTE, foto: null }))

  it('muestra lo que falta y solo deja enviar completa', async () => {
    const borrador = expediente({
      estado: 'borrador', faltantes: ['Foto tipo carné'], permisos: { revisar: false, descargar: true, enviar: true },
      elementos: [elemento(1, 'CI anverso', { tipo: 'documento_perfil', campo: null, tipo_documento: 1, editable: false }), elemento(2, 'Foto tipo carné', { tipo: 'imagen', entregado: false, archivo: null })],
    })
    miPrematricula.listar.mockResolvedValue([borrador])
    miPrematricula.obtener.mockResolvedValue(borrador)
    miPrematricula.subirArchivo.mockResolvedValue({ ...borrador, faltantes: [] })
    miPrematricula.enviar.mockResolvedValue({ ...borrador, estado: 'completada', faltantes: [] })
    renderApp('/aspirante/prematricula')

    expect(await screen.findByText('Falta: Foto tipo carné.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar prematrícula' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: /Sustituir CI anverso/ })).not.toBeInTheDocument()

    const foto = new File(['x'], 'foto.png', { type: 'image/png' })
    const entrada = screen.getByRole('button', { name: 'Subir Foto tipo carné' }).parentElement.querySelector('input[type=file]')
    expect(entrada).toHaveAttribute('accept', 'image/jpeg,image/png')
    fireEvent.change(entrada, { target: { files: [foto] } })
    await waitFor(() => expect(miPrematricula.subirArchivo).toHaveBeenCalledWith(5, 2, foto))

    fireEvent.click(screen.getByRole('button', { name: 'Enviar prematrícula' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Enviar prematrícula' })).getByRole('button', { name: 'Enviar' }))
    await waitFor(() => expect(miPrematricula.enviar).toHaveBeenCalledWith(5))
  })

  it('con correcciones muestra la observación y el documento del perfil se sustituye en el perfil', async () => {
    const conCorrecciones = expediente({
      estado: 'con_correcciones', permisos: { revisar: false, descargar: true, enviar: true },
      elementos: [elemento(1, 'CI anverso', { tipo: 'documento_perfil', campo: null, tipo_documento: 1, revision: 'rechazado', observacion: 'Ilegible', editable: true })],
    })
    miPrematricula.listar.mockResolvedValue([conCorrecciones])
    miPrematricula.obtener.mockResolvedValue(conCorrecciones)
    renderApp('/aspirante/prematricula')

    expect(await screen.findByText('Corrige: Ilegible')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sustituir en mi perfil' })).toHaveAttribute('href', '/aspirante/completar-perfil')
    expect(screen.getByRole('button', { name: 'Reenviar prematrícula' })).toBeInTheDocument()
  })

  it('sin plaza no hay prematrícula', async () => {
    miPrematricula.listar.mockResolvedValue([])
    renderApp('/aspirante/prematricula')

    expect(await screen.findByText('Todavía no tienes prematrícula')).toBeInTheDocument()
  })
})
