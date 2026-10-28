import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import { observaciones, solicitudesAdmin } from '../../../services/solicitudes'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/solicitudes', () => ({
  solicitudesAdmin: {
    ruta: '/s/', listar: vi.fn(), obtener: vi.fn(), validarIndice: vi.fn(), observar: vi.fn(),
    estadisticas: vi.fn(), exportarExcel: vi.fn(), exportarPdf: vi.fn(),
  },
  observaciones: { editar: vi.fn(), resolver: vi.fn(), reabrir: vi.fn() },
}))
vi.mock('../../../services/publico', async (importOriginal) => {
  const { publico: real } = await importOriginal()
  return { publico: { ...real, carreras: { ruta: '/c/', listar: vi.fn().mockResolvedValue({ count: 0, results: [] }) } } }
})

const SECRETARIO = perfil({
  rol: { codigo: 'secretario_facultad', nombre: 'Secretario', ambito: 'facultad' },
  permisos: ['solicitudes.ver', 'solicitudes.editar', 'solicitudes.exportar', 'solicitudes.documentos_descargar'],
})

const CARRERA = { prioridad: 1, estado: 'pendiente', estado_nombre: 'Pendiente', oferta: { id: 10, carrera_nombre: 'Ingeniería Informática', entidad_nombre: 'Facultad de Informática' } }
const FILA = {
  id: 4, aspirante_id: 2, nombre: 'María González', ci: '98042512345', indice_declarado: 92.5, indice_validado: null,
  estado: 'pendiente', estado_nombre: 'Pendiente', revision_documental_pendiente: false, observaciones_sin_resolver: 0,
  convocatoria: '1.ª 2026-2027', carreras: [CARRERA], confirmada_at: '2026-10-20T10:00:00Z', modificada_at: null,
}
const TIPOS = [
  { id: 1, nombre: 'CI anverso', afecta_elegibilidad: false },
  { id: 3, nombre: 'Certificación de estudios', afecta_elegibilidad: true },
]

function detalle(extra = {}) {
  return {
    ...FILA,
    created_at: '2026-10-19T10:00:00Z',
    aspirante: {
      id: 2, nombre: 'María', apellidos: 'González', ci: '98042512345', email: 'maria@nauta.cu', celular: '55123456',
      centro_trabajo: 'ETECSA', indice_declarado: 92.5, indice_validado: null, indice_validado_por: null, indice_validado_at: null,
      perfil_completo: true, foto: null,
    },
    documentos: TIPOS.map((tipo) => ({
      tipo, documento: { id: tipo.id, version: 1, nombre_original: 'doc.pdf', formato: 'PDF', tamano: 2048, subido_at: '2026-10-19T10:00:00Z', archivo: `/documentos/${tipo.id}/archivo/` },
    })),
    observaciones: [],
    historial: [{ id: 1, tipo: 'seleccion', tipo_nombre: 'Selección', descripcion: 'Cambió la selección de carreras', usuario: 'María González', created_at: '2026-10-19T10:00:00Z', antes: [], despues: [{ prioridad: 1, carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática' }] }],
    elegibilidad: { elegible: false, motivos: ['Índice académico sin validar'] },
    permisos: { revisar: true, validar_indice: true, descargar_documentos: true, historial_documentos: false },
    ...extra,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue(SECRETARIO)
  solicitudesAdmin.listar.mockResolvedValue({ count: 1, results: [FILA] })
  solicitudesAdmin.obtener.mockResolvedValue(detalle())
})

describe('listado de solicitudes', () => {
  it('muestra las solicitudes con enlace al detalle', async () => {
    renderApp('/admin/solicitudes')

    const enlace = await screen.findByRole('link', { name: 'María González' })
    expect(enlace).toHaveAttribute('href', '/admin/solicitudes/4')
    expect(screen.getByText('92.5 (declarado)')).toBeInTheDocument()
  })

  it('filtra por estado', async () => {
    renderApp('/admin/solicitudes')
    await screen.findByRole('link', { name: 'María González' })

    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'observada' } })

    await waitFor(() => expect(solicitudesAdmin.listar).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'observada' })))
  })
})

describe('detalle de la solicitud', () => {
  async function abrir() {
    renderApp('/admin/solicitudes/4')
    await screen.findByRole('heading', { name: 'María González' })
  }

  it('valida el índice', async () => {
    solicitudesAdmin.validarIndice.mockResolvedValue(detalle({ estado: 'en_revision' }))
    await abrir()

    fireEvent.change(screen.getByLabelText(/^Índice según la certificación/), { target: { value: '91.4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validar índice' }))

    await waitFor(() => expect(solicitudesAdmin.validarIndice).toHaveBeenCalledWith(4, 91.4))
    expect(await screen.findByText('En revisión')).toBeInTheDocument()
  })

  it('al observar propone si afecta la elegibilidad según el elemento', async () => {
    solicitudesAdmin.observar.mockResolvedValue(detalle({ estado: 'observada' }))
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Nueva observación' }))
    const dialogo = screen.getByRole('dialog', { name: 'Nueva observación' })
    const afecta = within(dialogo).getByLabelText(/^Afecta la elegibilidad/)
    expect(afecta).not.toBeChecked() // CI anverso
    fireEvent.change(within(dialogo).getByLabelText('Documento'), { target: { value: '3' } })
    expect(afecta).toBeChecked() // Certificación de estudios
    fireEvent.change(within(dialogo).getByLabelText('Qué observas'), { target: { value: 'foto' } })
    expect(afecta).not.toBeChecked()
    fireEvent.change(within(dialogo).getByLabelText('Qué observas'), { target: { value: 'indice' } })
    expect(afecta).toBeChecked()

    fireEvent.change(within(dialogo).getByLabelText(/^Observación/), { target: { value: ' No coincide ' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Observar' }))

    await waitFor(() =>
      expect(solicitudesAdmin.observar).toHaveBeenCalledWith(4, { objetivo: 'indice', tipo_documento: null, texto: 'No coincide', afecta_elegibilidad: true }),
    )
  })

  it('resuelve y reabre las observaciones propias', async () => {
    const observacion = {
      id: 7, objetivo: 'foto', tipo_documento: null, elemento: 'Foto', texto: 'Borrosa', afecta_elegibilidad: false,
      estado: 'corregida', estado_nombre: 'Corregida', entidad_nombre: 'Facultad de Informática', autor_nombre: 'Ana',
      created_at: '2026-10-20T10:00:00Z', corregida_at: '2026-10-21T10:00:00Z', resuelta_at: null, puede_gestionar: true,
    }
    solicitudesAdmin.obtener.mockResolvedValue(detalle({ observaciones: [observacion] }))
    observaciones.reabrir.mockResolvedValue({})
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Reabrir la observación sobre Foto' }))
    const dialogo = screen.getByRole('dialog', { name: 'Reabrir observación: Foto' })
    fireEvent.change(within(dialogo).getByLabelText(/^Motivo/), { target: { value: 'Sigue borrosa' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Reabrir' }))
    await waitFor(() => expect(observaciones.reabrir).toHaveBeenCalledWith(7, 'Sigue borrosa'))

    fireEvent.click(screen.getByRole('button', { name: 'Resolver la observación sobre Foto' }))
    fireEvent.click(within(screen.getByRole('dialog', { name: 'Resolver observación' })).getByRole('button', { name: 'Resolver observación' }))
    await waitFor(() => expect(observaciones.resolver).toHaveBeenCalledWith(7))
  })

  it('las observaciones ajenas no se gestionan', async () => {
    solicitudesAdmin.obtener.mockResolvedValue(
      detalle({
        observaciones: [{ id: 8, elemento: 'Foto', texto: 'x', estado: 'abierta', entidad_nombre: 'CUM Banes', autor_nombre: 'Luis', created_at: '2026-10-20T10:00:00Z', puede_gestionar: false }],
      }),
    )
    await abrir()

    expect(screen.getByText(/CUM Banes/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Resolver la observación/ })).not.toBeInTheDocument()
  })

  it('sin permiso de descarga no ofrece ver documentos', async () => {
    solicitudesAdmin.obtener.mockResolvedValue(
      detalle({
        permisos: { revisar: true, validar_indice: true, descargar_documentos: false, historial_documentos: false },
        documentos: TIPOS.map((tipo) => ({ tipo, documento: { id: tipo.id, version: 1, nombre_original: 'doc.pdf', formato: 'PDF', tamano: 10, subido_at: '2026-10-19T10:00:00Z', archivo: null } })),
      }),
    )
    await abrir()

    expect(screen.getByText(/no tiene permiso para abrir los documentos/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Ver / })).not.toBeInTheDocument()
  })

  it('muestra el historial de la selección', async () => {
    await abrir()

    expect(screen.getByText('Cambió la selección de carreras')).toBeInTheDocument()
    expect(screen.getByText(/Después: 1\. Ingeniería Informática \(Facultad de Informática\)/)).toBeInTheDocument()
  })
})

describe('estadísticas', () => {
  it('sin convocatorias muestra un aviso neutro, no un error', async () => {
    solicitudesAdmin.estadisticas.mockResolvedValue({
      convocatoria: null,
      totales: { solicitudes: 0, plazas: 0, por_estado: {} },
      termometro: [], por_carrera: [], evolucion: [],
    })
    renderApp('/admin/solicitudes')
    fireEvent.click(await screen.findByRole('tab', { name: 'Estadísticas' }))

    expect(await screen.findByText('Todavía no hay convocatorias de solicitud')).toBeInTheDocument()
  })

  it('muestra el termómetro frente al plan', async () => {
    solicitudesAdmin.estadisticas.mockResolvedValue({
      convocatoria: { id: 1, anio_academico: '2026-2027', numero: 1 },
      totales: { solicitudes: 12, plazas: 10, por_estado: { pendiente: 8, en_revision: 3, observada: 1, otorgada: 0, no_seleccionado: 0 } },
      termometro: [{ oferta: 10, carrera: 'Ingeniería Informática', entidad: 'Facultad de Informática', plazas: 10, solicitudes: 12, primera_opcion: 7 }],
      por_carrera: [{ carrera: 'Ingeniería Informática', plazas: 10, solicitudes: 12, primera_opcion: 7 }],
      evolucion: [{ dia: '2026-10-20', total: 5 }, { dia: '2026-10-21', total: 7 }],
    })
    renderApp('/admin/solicitudes')
    fireEvent.click(await screen.findByRole('tab', { name: 'Estadísticas' }))

    expect(await screen.findByText('12 solicitudes de 10 plazas (120 %)')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Solicitudes confirmadas por día' })).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('21/10')
    fireEvent.mouseEnter(screen.getByLabelText('21/10: 7 solicitudes'))
    expect(screen.getByRole('status')).toHaveTextContent('7 solicitudes')
  })
})
