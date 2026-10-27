import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import { convocatoriasSolicitud } from '../../../services/convocatorias'
import { otorgamientos } from '../../../services/otorgamiento'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/convocatorias', () => ({ convocatoriasSolicitud: { ruta: '/c/', listar: vi.fn() } }))
vi.mock('../../../services/otorgamiento', () => {
  const listarResultados = vi.fn()
  return {
    otorgamientos: {
      listar: vi.fn(), obtener: vi.fn(), previsualizar: vi.fn(), generar: vi.fn(), ajustes: vi.fn(), ajustar: vi.fn(),
      anularAjuste: vi.fn(), aprobar: vi.fn(), publicar: vi.fn(), exportarExcel: vi.fn(), exportarPdf: vi.fn(),
      listarResultados,
      resultados: () => ({ ruta: '/r/', listar: listarResultados }),
    },
  }
})

const CONVOCATORIA = { id: 1, anio_academico: '2026-2027', numero: 1, estado: 'cerrada' }
const SECRETARIA = perfil({ rol: { codigo: 'secretaria_general', nombre: 'SG', ambito: 'global' }, permisos: ['otorgamiento.ver', 'otorgamiento.generar', 'convocatorias.ver'] })
const JEFE = perfil({ permisos: ['otorgamiento.ver', 'otorgamiento.aprobar', 'otorgamiento.exportar'] })
const VICERRECTOR = perfil({ rol: { codigo: 'vicerrector', nombre: 'VR', ambito: 'global' }, permisos: ['otorgamiento.ver', 'otorgamiento.publicar'] })

function otorgamiento(extra = {}) {
  return {
    id: 3, convocatoria: { id: 1, anio_academico: '2026-2027', numero: 1 }, estado: 'revision_ci', estado_nombre: 'Revisión del Jefe CI',
    resumen: {}, segunda_convocatoria: null, generado_por: 'SG', generado_at: '2026-12-01T10:00:00Z',
    aprobado_por: null, aprobado_at: null, publicado_por: null, publicado_at: null,
    totales: { resultados: 3, elegibles: 2, otorgadas: 2, plazas: 2 },
    plazas: [{ oferta: 10, carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática', plazas: 2, otorgadas: 2 }],
    permisos: { editar: true, aprobar: true, publicar: false, exportar: true },
    ...extra,
  }
}

const ANA = {
  id: 7, solicitud: 1, aspirante: 2, aspirante_nombre: 'Ana Pérez', indice_utilizado: 95, posicion_ranking: 1, motivo_exclusion: '',
  opciones: [
    { opcion: 101, oferta: 10, prioridad: 1, carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática' },
    { opcion: 102, oferta: 11, prioridad: 2, carrera: 'Derecho', entidad: 'CUM Banes' },
  ],
  otorgada: 101, carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática', prioridad: 1, tipo: 'automatica', tipo_nombre: 'Automática', opciones_quitadas: [],
}
const PEPE = { ...ANA, id: 8, aspirante_nombre: 'Pepe Gil', posicion_ranking: null, motivo_exclusion: 'Tiene observaciones sin resolver', otorgada: null, carrera: '', entidad: '', prioridad: null, tipo: '' }

beforeEach(() => {
  vi.clearAllMocks()
  otorgamientos.listar.mockResolvedValue([])
  otorgamientos.listarResultados.mockResolvedValue({ count: 2, results: [ANA, PEPE] })
  otorgamientos.ajustes.mockResolvedValue([])
  convocatoriasSolicitud.listar.mockResolvedValue({ count: 1, results: [CONVOCATORIA] })
})

async function abrir(usuario) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp('/admin/otorgamiento')
  await screen.findByRole('heading', { name: 'Otorgamiento' })
}

describe('generar', () => {
  it('muestra el resumen de elegibilidad y exige confirmar', async () => {
    otorgamientos.previsualizar.mockResolvedValue({
      solicitudes: 3, elegibles: 2, no_elegibles: 1, plazas: 2, motivos: [{ motivo: 'Índice académico sin validar', cantidad: 1 }],
    })
    otorgamientos.generar.mockResolvedValue(otorgamiento())
    await abrir(SECRETARIA)

    fireEvent.click(await screen.findByRole('button', { name: 'Generar otorgamiento' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Generar otorgamiento' })
    expect(within(dialogo).getByText('Índice académico sin validar: 1')).toBeInTheDocument()
    const generar = within(dialogo).getByRole('button', { name: 'Generar' })
    expect(generar).toBeDisabled()

    fireEvent.click(within(dialogo).getByLabelText(/no se puede volver a generar/))
    fireEvent.click(generar)

    await waitFor(() => expect(otorgamientos.generar).toHaveBeenCalledWith(1))
    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument()
  })
})

describe('revisión y ajustes', () => {
  it('muestra el ranking con los no elegibles', async () => {
    otorgamientos.listar.mockResolvedValue([otorgamiento()])
    await abrir(JEFE)

    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('No elegible: Tiene observaciones sin resolver')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajustar a Pepe Gil' })).not.toBeInTheDocument()
  })

  it('ajusta con justificación y muestra la cascada', async () => {
    otorgamientos.listar.mockResolvedValue([otorgamiento()])
    otorgamientos.obtener.mockResolvedValue(otorgamiento())
    otorgamientos.ajustar.mockResolvedValue({
      ajuste: { id: 1 }, cambios: [{ resultado: 7, aspirante: 'Ana Pérez', antes: 'Ingeniería Informática — Facultad de Informática', despues: 'Derecho — CUM Banes' }],
    })
    await abrir(JEFE)

    fireEvent.click(await screen.findByRole('button', { name: 'Ajustar a Ana Pérez' }))
    const dialogo = screen.getByRole('dialog', { name: 'Ajustar a Ana Pérez' })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Otorgar esta' }))
    expect(await within(dialogo).findByText('La justificación es obligatoria.')).toBeInTheDocument()

    fireEvent.change(within(dialogo).getByLabelText(/^Justificación/), { target: { value: 'Pidió el cambio' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Otorgar esta' }))

    await waitFor(() => expect(otorgamientos.ajustar).toHaveBeenCalledWith(3, { resultado: 7, tipo: 'otorgar', opcion: 102, justificacion: 'Pidió el cambio' }))
    expect(await within(dialogo).findByText('Derecho — CUM Banes')).toBeInTheDocument()
  })

  it('el Jefe CI aprueba', async () => {
    otorgamientos.listar.mockResolvedValue([otorgamiento()])
    otorgamientos.aprobar.mockResolvedValue(otorgamiento({ estado: 'aprobacion', estado_nombre: 'Aprobación del Vicerrector', permisos: { editar: false, aprobar: false, publicar: false, exportar: true } }))
    await abrir(JEFE)

    fireEvent.click(await screen.findByRole('button', { name: 'Aprobar' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Aprobar otorgamiento' })).getByRole('button', { name: 'Aprobar otorgamiento' }))

    await waitFor(() => expect(otorgamientos.aprobar).toHaveBeenCalledWith(3))
    expect(await screen.findByText(/El Vicerrector de Formación revisa/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Aprobar' })).not.toBeInTheDocument()
  })

  it('el Vicerrector publica indicando si habrá segunda convocatoria', async () => {
    otorgamientos.listar.mockResolvedValue([otorgamiento({ estado: 'aprobacion', estado_nombre: 'Aprobación del Vicerrector', permisos: { editar: true, aprobar: false, publicar: true, exportar: false } })])
    otorgamientos.publicar.mockResolvedValue(otorgamiento({ estado: 'publicado', estado_nombre: 'Publicado', permisos: { editar: false, aprobar: false, publicar: false, exportar: false } }))
    await abrir(VICERRECTOR)

    fireEvent.click(await screen.findByRole('button', { name: 'Aprobar y publicar' }))
    const dialogo = screen.getByRole('dialog', { name: 'Aprobar y publicar' })
    fireEvent.click(within(dialogo).getByLabelText(/Habrá segunda convocatoria/))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Aprobar y publicar' }))

    await waitFor(() => expect(otorgamientos.publicar).toHaveBeenCalledWith(3, true))
    expect(await screen.findByText(/Ya no admite cambios/)).toBeInTheDocument()
  })
})
