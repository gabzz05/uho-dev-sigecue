import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../../../services/auth'
import * as nomencladores from '../../../services/nomencladores'
import { roles, usuarios } from '../../../services/usuarios'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))

vi.mock('../../../services/nomencladores', () => {
  const recurso = (ruta) => ({ ruta, listar: vi.fn() })
  return { municipios: recurso('m'), facultades: recurso('f'), cumFum: recurso('c'), areas: recurso('a'), departamentos: recurso('d'), cargos: recurso('g'), carreras: recurso('r') }
})

vi.mock('../../../services/usuarios', () => ({
  usuarios: {
    ruta: '/admin/usuarios/', listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn(),
    rolesAsignables: vi.fn(), bloquear: vi.fn(), desbloquear: vi.fn(),
  },
  roles: { ruta: '/admin/roles/', listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn(), catalogo: vi.fn() },
}))

const pagina = (results) => ({ count: results.length, results })

const ROLES = [
  { codigo: 'secretario_facultad', nombre: 'Secretario(a) Facultad', ambito: 'facultad', requiere_area: false },
  { codigo: 'jefe_area_facultad', nombre: 'Jefe de Área Facultad', ambito: 'facultad', requiere_area: true },
  { codigo: 'vicerrector', nombre: 'Vicerrector de Formación', ambito: 'global', requiere_area: false },
]

const SECRETARIA = {
  id: 5, username: 'ana', first_name: 'Ana', last_name: 'Pérez', email: 'ana@uho.edu.cu', ci: '', celular: '',
  rol: 'secretario_facultad', facultad: 3, cum_fum: null, entidad: { tipo: 'facultad', id: 3, nombre: 'Fac. Informática' },
  area: null, area_nombre: null, cargo: null, origen: 'local', is_active: true, bloqueado_hasta: null, last_login: null,
}

const SUPERADMIN = perfil({ permisos: ['*'], es_superadmin: true, rol: null })
const ADMIN_LOCAL = perfil({
  username: 'admin_fac',
  rol: { codigo: 'admin_facultad', nombre: 'Admin Facultad', ambito: 'facultad' },
  entidad: { tipo: 'facultad', id: 3, nombre: 'Fac. Informática' },
  permisos: ['usuarios.ver', 'usuarios.crear', 'usuarios.editar', 'nomencladores.ver'],
})

beforeEach(() => {
  vi.clearAllMocks()
  Object.values(nomencladores).forEach((r) => r.listar.mockResolvedValue(pagina([])))
  nomencladores.facultades.listar.mockResolvedValue(pagina([{ id: 3, nombre: 'Fac. Informática' }]))
  nomencladores.areas.listar.mockResolvedValue(
    pagina([
      { id: 7, nombre: 'Software', facultad: 3, cum_fum: null, entidad_nombre: 'Fac. Informática' },
      { id: 8, nombre: 'Contabilidad', facultad: 4, cum_fum: null, entidad_nombre: 'Fac. Económicas' },
    ]),
  )
  usuarios.listar.mockResolvedValue(pagina([SECRETARIA]))
  usuarios.rolesAsignables.mockResolvedValue(ROLES)
})

async function abrir(usuario = SUPERADMIN) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp('/admin/usuarios')
  return screen.findByText('Ana Pérez')
}

function llenarBasicos(dialogo) {
  fireEvent.change(within(dialogo).getByLabelText(/^Nombre \*/), { target: { value: 'Luis' } })
  fireEvent.change(within(dialogo).getByLabelText(/^Nombre de usuario/), { target: { value: 'luis' } })
  fireEvent.change(within(dialogo).getByLabelText(/^Correo/), { target: { value: 'luis@uho.edu.cu' } })
  fireEvent.change(within(dialogo).getByLabelText(/^Contraseña/), { target: { value: 'Clave-Segura-1' } })
}

describe('Usuarios', () => {
  it('lista usuarios con su rol y entidad, sin opción de borrar', async () => {
    const celda = (await abrir()).closest('tr')

    expect(within(celda).getByText('Secretario(a) Facultad')).toBeInTheDocument()
    expect(within(celda).getByText('Fac. Informática')).toBeInTheDocument()
    expect(within(celda).queryByRole('button', { name: /Eliminar/ })).not.toBeInTheDocument()
  })

  it('un rol global elige la Facultad de un rol local', async () => {
    usuarios.crear.mockResolvedValue({ ...SECRETARIA, id: 9, first_name: 'Luis', last_name: '' })
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) usuario/ }))
    const dialogo = screen.getByRole('dialog')
    llenarBasicos(dialogo)
    fireEvent.change(within(dialogo).getByLabelText(/^Rol/), { target: { value: 'secretario_facultad' } })
    await within(dialogo).findByRole('option', { name: 'Fac. Informática' })
    fireEvent.change(within(dialogo).getByLabelText(/^Facultad/), { target: { value: '3' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usuarios.crear).toHaveBeenCalled())
    expect(usuarios.crear.mock.calls[0][0]).toMatchObject({
      username: 'luis', rol: 'secretario_facultad', facultad: '3', cum_fum: null, area: null, password: 'Clave-Segura-1',
    })
  })

  it('un rol local no elige entidad: la API usa la suya', async () => {
    usuarios.crear.mockResolvedValue({ ...SECRETARIA, id: 9 })
    await abrir(ADMIN_LOCAL)

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) usuario/ }))
    const dialogo = screen.getByRole('dialog')
    llenarBasicos(dialogo)
    fireEvent.change(within(dialogo).getByLabelText(/^Rol/), { target: { value: 'secretario_facultad' } })
    expect(within(dialogo).queryByLabelText(/^Facultad/)).not.toBeInTheDocument()
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usuarios.crear).toHaveBeenCalled())
    expect(usuarios.crear.mock.calls[0][0]).not.toHaveProperty('facultad')
  })

  it('el Jefe de Área solo puede elegir áreas de su entidad', async () => {
    await abrir(ADMIN_LOCAL)

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) usuario/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Rol/), { target: { value: 'jefe_area_facultad' } })

    const area = within(dialogo).getByLabelText(/^Área/)
    expect(within(area).getByRole('option', { name: 'Software' })).toBeInTheDocument()
    expect(within(area).queryByRole('option', { name: 'Contabilidad' })).not.toBeInTheDocument()
  })

  it('valida el rol y la contraseña antes de enviar', async () => {
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) usuario/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await within(dialogo).findByText('Selecciona el rol.')).toBeInTheDocument()
    expect(within(dialogo).getByText('La contraseña debe tener al menos 8 caracteres.')).toBeInTheDocument()
    expect(usuarios.crear).not.toHaveBeenCalled()
  })

  it('al editar no envía la contraseña si se deja vacía', async () => {
    usuarios.actualizar.mockResolvedValue(SECRETARIA)
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Editar Ana Pérez' }))
    const dialogo = screen.getByRole('dialog')
    expect(within(dialogo).getByLabelText(/^Nombre de usuario/)).toBeDisabled()
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usuarios.actualizar).toHaveBeenCalled())
    expect(usuarios.actualizar.mock.calls[0][1]).not.toHaveProperty('password')
  })

  it('bloquear usa el endpoint de bloqueo', async () => {
    usuarios.bloquear.mockResolvedValue({})
    await abrir()

    fireEvent.click(screen.getByRole('button', { name: 'Bloquear Ana Pérez' }))

    await waitFor(() => expect(usuarios.bloquear).toHaveBeenCalledWith(5))
    expect(await screen.findByText('Se bloqueó: Ana Pérez.')).toBeInTheDocument()
  })

  it('muestra el bloqueo temporal y permite levantarlo', async () => {
    usuarios.listar.mockResolvedValue(pagina([{ ...SECRETARIA, bloqueado_hasta: new Date(Date.now() + 600000).toISOString() }]))
    usuarios.desbloquear.mockResolvedValue({})
    const celda = (await abrir()).closest('tr')

    expect(within(celda).getByText('Bloqueo temporal')).toBeInTheDocument()
    fireEvent.click(within(celda).getByRole('button', { name: 'Levantar bloqueo temporal de Ana Pérez' }))

    await waitFor(() => expect(usuarios.desbloquear).toHaveBeenCalledWith(5))
  })
})

describe('Roles', () => {
  const CATALOGO = [
    { modulo: 'dashboard', nombre: 'Dashboard', acciones: [{ codigo: 'dashboard.ver', accion: 'ver', nombre: 'Ver' }] },
    {
      modulo: 'logs',
      nombre: 'Logs de auditoría',
      acciones: [{ codigo: 'logs.ver', accion: 'ver', nombre: 'Ver' }],
    },
    {
      modulo: 'solicitudes',
      nombre: 'Solicitudes',
      acciones: [
        { codigo: 'solicitudes.ver', accion: 'ver', nombre: 'Ver' },
        { codigo: 'solicitudes.editar', accion: 'editar', nombre: 'Editar' },
      ],
    },
  ]
  const VICERRECTOR = { id: 4, codigo: 'vicerrector', nombre: 'Vicerrector de Formación', ambito: 'global', requiere_area: false, es_sistema: true, activo: true, descripcion: '', permisos: ['dashboard.ver'] }
  const AUDITOR = { id: 20, codigo: 'auditor', nombre: 'Auditor', ambito: 'global', requiere_area: false, es_sistema: false, activo: true, descripcion: '', permisos: [] }

  beforeEach(() => {
    roles.listar.mockResolvedValue(pagina([VICERRECTOR, AUDITOR]))
    roles.catalogo.mockResolvedValue(CATALOGO)
  })

  async function abrirRoles() {
    auth.restaurarSesion.mockResolvedValue(SUPERADMIN)
    renderApp('/admin/roles')
    await screen.findByText('Vicerrector de Formación')
  }

  it('solo los roles propios se pueden eliminar', async () => {
    await abrirRoles()

    expect(screen.queryByRole('button', { name: 'Eliminar Vicerrector de Formación' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Eliminar Auditor' })).toBeInTheDocument()
  })

  it('en un rol del sistema el código y el ámbito no se editan', async () => {
    await abrirRoles()

    fireEvent.click(screen.getByRole('button', { name: 'Editar Vicerrector de Formación' }))
    const dialogo = screen.getByRole('dialog')

    expect(within(dialogo).getByLabelText(/^Código/)).toBeDisabled()
    expect(within(dialogo).getByLabelText(/^Ámbito/)).toBeDisabled()
  })

  it('la matriz marca permisos sueltos y módulos completos', async () => {
    roles.actualizar.mockResolvedValue(VICERRECTOR)
    await abrirRoles()

    fireEvent.click(screen.getByRole('button', { name: 'Editar Vicerrector de Formación' }))
    const dialogo = screen.getByRole('dialog')
    await within(dialogo).findByLabelText('Ver en Logs de auditoría')
    fireEvent.click(within(dialogo).getByLabelText('Ver en Logs de auditoría'))
    fireEvent.click(within(dialogo).getByLabelText('Todos los permisos de Solicitudes'))
    fireEvent.click(within(dialogo).getByLabelText('Ver en Dashboard'))
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(roles.actualizar).toHaveBeenCalled())
    expect(roles.actualizar.mock.calls[0][1].permisos).toEqual(['logs.ver', 'solicitudes.editar', 'solicitudes.ver'])
  })

  it('el código de un rol nuevo debe ser un identificador', async () => {
    await abrirRoles()

    fireEvent.click(screen.getByRole('button', { name: /Nuevo\(a\) rol/ }))
    const dialogo = screen.getByRole('dialog')
    fireEvent.change(within(dialogo).getByLabelText(/^Código/), { target: { value: 'Con Espacios' } })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await within(dialogo).findByText(/Usa solo minúsculas/)).toBeInTheDocument()
    expect(roles.crear).not.toHaveBeenCalled()
  })
})
