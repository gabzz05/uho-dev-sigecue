import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import * as nomencladores from '../../../services/nomencladores'
import { lineasPlan, planes } from '../../../services/planPlazas'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))
vi.mock('../../../services/planPlazas', () => ({
  planes: {
    ruta: '/admin/plan-plazas/', listar: vi.fn(), obtener: vi.fn(), crear: vi.fn(),
    enviar: vi.fn(), cargarOferta: vi.fn(), cerrarRevision: vi.fn(), generarVersionFinal: vi.fn(), enviarPropuesta: vi.fn(),
    aprobar: vi.fn(), devolver: vi.fn(), complementaria: vi.fn(), historial: vi.fn(), comentarios: vi.fn(), comentar: vi.fn(),
    exportarPdf: vi.fn(), exportarExcel: vi.fn(),
  },
  lineasPlan: { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn(), responder: vi.fn(), decidir: vi.fn() },
}))
vi.mock('../../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn() })
  return { carreras: recurso('r'), facultades: recurso('f'), cumFum: recurso('c'), municipios: recurso('m'), areas: recurso('a'), departamentos: recurso('d'), cargos: recurso('g') }
})

const FACULTAD = { tipo: 'facultad', id: 3, nombre: 'Fac. Informática' }
const LINEA = {
  id: 11, carrera: 1, carrera_nombre: 'Ingeniería Informática', entidad: FACULTAD, origen: 'ci', plazas_propuestas: 80,
  accion_entidad: 'aceptar', plazas_entidad: null, comentario_entidad: '', propuesta_entidad: 80,
  decision_ci: 'aceptar', decision_ci_nombre: 'Acepta la propuesta de la entidad', plazas_decision: null, comentario_ci: '',
  resultado: 80, plazas_aprobadas: null,
}

function plan(estado, acciones, extra = {}) {
  return {
    id: 5, anio_academico: '2026-2027', es_complementario: false, estado, version: 0, notas: '', observaciones_vicerrector: '',
    aprobado_por_nombre: '', fecha_aprobacion: null, totales: { lineas: 1, plazas_propuestas: 80, plazas_aprobadas: 0 },
    acciones, entidades: [{ id: 1, entidad: FACULTAD, estado: 'pendiente', comentario: '', enviada_por_nombre: '', enviada_at: null }],
    ...extra,
  }
}

const JEFE_CI = perfil({ permisos: ['plan_plazas.ver', 'plan_plazas.crear', 'plan_plazas.editar'] })
const ADMIN_LOCAL = perfil({
  rol: { codigo: 'admin_facultad', nombre: 'Admin Facultad', ambito: 'facultad' }, entidad: FACULTAD, permisos: ['plan_plazas.ver', 'plan_plazas.editar'],
})

beforeEach(() => {
  vi.clearAllMocks()
  lineasPlan.listar.mockResolvedValue([LINEA])
  planes.historial.mockResolvedValue([])
  planes.comentarios.mockResolvedValue([])
  Object.values(nomencladores).forEach((r) => r.listar.mockResolvedValue({ count: 1, results: [{ id: 3, nombre: 'Fac. Informática' }] }))
})

async function abrir(datosPlan, usuario = JEFE_CI) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  planes.obtener.mockResolvedValue(datosPlan)
  renderApp('/admin/plan-plazas/5')
  await screen.findByRole('heading', { name: 'Plan de plazas 2026-2027' })
}

const confirmar = async (titulo, boton = titulo) =>
  fireEvent.click(within(await screen.findByRole('dialog', { name: titulo })).getByRole('button', { name: boton }))

describe('listado', () => {
  it('la CI crea un plan y abre su detalle', async () => {
    planes.listar.mockResolvedValue({ count: 0, results: [] })
    planes.crear.mockResolvedValue(plan('borrador', ['editar_lineas', 'enviar']))
    planes.obtener.mockResolvedValue(plan('borrador', ['editar_lineas', 'enviar']))
    auth.restaurarSesion.mockResolvedValue(JEFE_CI)
    renderApp('/admin/plan-plazas')

    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo plan' }))
    fireEvent.change(screen.getByLabelText(/^Año académico/), { target: { value: '2026-2027' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('heading', { name: 'Plan de plazas 2026-2027' })).toBeInTheDocument()
    expect(planes.crear).toHaveBeenCalledWith({ anio_academico: '2026-2027', notas: '' })
  })

  it('un rol local no crea planes', async () => {
    planes.listar.mockResolvedValue({ count: 0, results: [] })
    auth.restaurarSesion.mockResolvedValue(ADMIN_LOCAL)
    renderApp('/admin/plan-plazas')

    await screen.findByText('Todavía no hay planes de plazas.')
    expect(screen.queryByRole('button', { name: 'Nuevo plan' })).not.toBeInTheDocument()
  })
})

describe('borrador (CI)', () => {
  it('muestra el paso actual y envía tras confirmar', async () => {
    planes.enviar.mockResolvedValue({})
    await abrir(plan('borrador', ['editar_lineas', 'cargar_oferta', 'enviar']))

    expect(screen.getByText('Borrador de la CI').closest('li')).toHaveAttribute('aria-current', 'step')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar a las entidades' }))
    await confirmar('Enviar a las entidades')

    await waitFor(() => expect(planes.enviar).toHaveBeenCalledWith(5))
    expect(await screen.findByText('El plan se envió a las entidades.')).toBeInTheDocument()
  })

  it('agrega una carrera eligiendo la entidad y edita plazas', async () => {
    lineasPlan.crear.mockResolvedValue({})
    lineasPlan.actualizar.mockResolvedValue({})
    await abrir(plan('borrador', ['editar_lineas', 'enviar']))

    fireEvent.click(await screen.findByRole('button', { name: 'Agregar carrera' }))
    const dialogo = screen.getByRole('dialog', { name: 'Agregar carrera al plan' })
    await within(dialogo).findAllByRole('option', { name: 'Fac. Informática' })
    fireEvent.change(within(dialogo).getByLabelText(/^Carrera/), { target: { value: '3' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Facultad o CUM/), { target: { value: 'facultad:3' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Plazas/), { target: { value: '25' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(lineasPlan.crear).toHaveBeenCalledWith({ plan: 5, carrera: '3', facultad: '3', plazas: 25 }))

    fireEvent.click(screen.getByRole('button', { name: 'Editar Ingeniería Informática (Fac. Informática)' }))
    const edicion = screen.getByRole('dialog')
    fireEvent.change(within(edicion).getByLabelText(/^Plazas/), { target: { value: '90' } })
    fireEvent.click(within(edicion).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(lineasPlan.actualizar).toHaveBeenCalledWith(11, 90))
  })
})

describe('revisión de la entidad', () => {
  it('modificar exige justificación y envía la respuesta', async () => {
    lineasPlan.responder.mockResolvedValue({})
    await abrir(plan('enviado', ['responder', 'enviar_propuesta', 'comentar']), ADMIN_LOCAL)

    fireEvent.click(await screen.findByRole('button', { name: 'Responder Ingeniería Informática' }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Respuesta de la entidad/), { target: { value: 'modificar' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Plazas que propone/), { target: { value: '100' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    expect(await within(dialogo).findByText('Justifica el cambio.')).toBeInTheDocument()

    fireEvent.change(within(dialogo).getByLabelText(/^Justificación/), { target: { value: 'Hay demanda' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(lineasPlan.responder).toHaveBeenCalledWith(11, { accion: 'modificar', plazas: 100, comentario: 'Hay demanda' }))
  })

  it('solicita una carrera y envía la propuesta', async () => {
    lineasPlan.crear.mockResolvedValue({})
    planes.enviarPropuesta.mockResolvedValue({})
    await abrir(plan('enviado', ['responder', 'enviar_propuesta']), ADMIN_LOCAL)

    fireEvent.click(await screen.findByRole('button', { name: 'Solicitar carrera' }))
    const dialogo = screen.getByRole('dialog', { name: 'Solicitar agregar una carrera' })
    expect(within(dialogo).queryByLabelText(/Facultad o CUM/)).not.toBeInTheDocument()
    await within(dialogo).findByRole('option', { name: 'Fac. Informática' })
    fireEvent.change(within(dialogo).getByLabelText(/^Carrera/), { target: { value: '3' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Plazas/), { target: { value: '30' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Justificación/), { target: { value: 'Nueva demanda' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(lineasPlan.crear).toHaveBeenCalledWith({ plan: 5, carrera: '3', plazas: 30, comentario: 'Nueva demanda' }))

    fireEvent.click(screen.getByRole('button', { name: 'Enviar propuesta' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(planes.enviarPropuesta).toHaveBeenCalledWith(5, ''))
  })

  it('el Jefe de Área solo comenta', async () => {
    planes.comentar.mockResolvedValue({ id: 1, texto: 'Sugiero 90', usuario_nombre: 'Ana (Jefe de Área Facultad)', created_at: '2026-10-25T10:00:00Z', entidad: FACULTAD })
    await abrir(plan('enviado', ['comentar']), perfil({ rol: { codigo: 'jefe_area_facultad', nombre: 'Jefe de Área', ambito: 'facultad' }, permisos: ['plan_plazas.ver', 'plan_plazas.editar'] }))

    expect(screen.queryByRole('button', { name: /Responder/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Comentarios' }))
    fireEvent.change(await screen.findByLabelText('Nuevo comentario'), { target: { value: 'Sugiero 90' } })
    fireEvent.click(screen.getByRole('button', { name: 'Comentar' }))

    expect(await screen.findByText('Sugiero 90')).toBeInTheDocument()
    expect(planes.comentar).toHaveBeenCalledWith(5, 'Sugiero 90')
  })
})

describe('revisión de la CI', () => {
  it('pasar a revisión con entidades pendientes fuerza el paso', async () => {
    planes.cerrarRevision.mockResolvedValue({})
    await abrir(plan('enviado', ['cerrar_revision']))

    fireEvent.click(screen.getByRole('button', { name: 'Pasar a revisión de la CI' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Pasar a la revisión de la CI' })
    expect(dialogo).toHaveTextContent('Faltan 1 entidad(es)')
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Forzar y continuar' }))

    await waitFor(() => expect(planes.cerrarRevision).toHaveBeenCalledWith(5, true))
  })

  it('decide otra cantidad con comentario y genera la versión final', async () => {
    lineasPlan.decidir.mockResolvedValue({})
    planes.generarVersionFinal.mockResolvedValue({})
    await abrir(plan('revision_ci', ['decidir', 'generar_version_final'], { observaciones_vicerrector: 'Revisar Informática' }))

    expect(screen.getByText('Revisar Informática')).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Decidir Ingeniería Informática (Fac. Informática)' }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Decisión/), { target: { value: 'otro' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Plazas/), { target: { value: '90' } })
    fireEvent.change(within(dialogo).getByLabelText(/^Comentario/), { target: { value: 'Capacidad' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(lineasPlan.decidir).toHaveBeenCalledWith(11, { decision: 'otro', plazas: 90, comentario: 'Capacidad' }))

    fireEvent.click(screen.getByRole('button', { name: 'Generar versión final' }))
    await confirmar('Generar versión final')
    await waitFor(() => expect(planes.generarVersionFinal).toHaveBeenCalledWith(5))
  })
})

describe('aprobación', () => {
  const VICERRECTOR = perfil({ rol: { codigo: 'vicerrector', nombre: 'Vicerrector de Formación', ambito: 'global' }, permisos: ['plan_plazas.ver'] })

  it('el Vicerrector aprueba y publica', async () => {
    planes.aprobar.mockResolvedValue({})
    await abrir(plan('en_aprobacion', ['aprobar', 'devolver'], { version: 1 }), VICERRECTOR)

    fireEvent.click(screen.getByRole('button', { name: 'Aprobar y publicar' }))
    await confirmar('Aprobar y publicar')

    await waitFor(() => expect(planes.aprobar).toHaveBeenCalledWith(5))
  })

  it('devolver exige observaciones', async () => {
    planes.devolver.mockResolvedValue({})
    await abrir(plan('en_aprobacion', ['aprobar', 'devolver'], { version: 1 }), VICERRECTOR)

    fireEvent.click(screen.getByRole('button', { name: 'Devolver' }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    expect(await within(dialogo).findByText('Escribe las observaciones.')).toBeInTheDocument()

    fireEvent.change(within(dialogo).getByLabelText(/^Observaciones/), { target: { value: 'Revisar Derecho' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(planes.devolver).toHaveBeenCalledWith(5, 'Revisar Derecho'))
  })
})

describe('publicado', () => {
  it('exporta y crea la versión complementaria', async () => {
    planes.exportarExcel.mockResolvedValue(new Blob(['x']))
    planes.complementaria.mockResolvedValue({ id: 9 })
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    lineasPlan.listar.mockResolvedValue([{ ...LINEA, plazas_aprobadas: 90 }])
    await abrir(plan('publicado', ['exportar', 'crear_complementaria'], { version: 1, aprobado_por_nombre: 'Rosa Díaz', fecha_aprobacion: '2026-10-25T10:00:00Z' }))

    expect(screen.getByText(/Aprobado por Rosa Díaz/)).toBeInTheDocument()
    expect(screen.getByText(/Total:/)).toHaveTextContent('Total: 90 plazas')
    fireEvent.click(screen.getByRole('button', { name: 'Excel' }))
    await waitFor(() => expect(planes.exportarExcel).toHaveBeenCalledWith(5))

    planes.obtener.mockResolvedValue(plan('borrador', ['editar_lineas', 'enviar'], { id: 9, es_complementario: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Versión complementaria' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(planes.complementaria).toHaveBeenCalledWith(5, ''))
    expect(await screen.findByText('Versión complementaria')).toBeInTheDocument()
  })
})
