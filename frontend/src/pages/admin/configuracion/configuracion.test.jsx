import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IdentidadProvider, useIdentidad } from '../../../hooks/useIdentidad'
import * as auth from '../../../services/auth'
import * as config from '../../../services/configuracion'
import { perfil, renderApp } from '../../../test/renderApp'

vi.mock('../../../services/auth', () => ({ restaurarSesion: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }))

vi.mock('../../../services/configuracion', () => ({
  obtenerIdentidad: vi.fn(),
  parametros: { obtener: vi.fn(), guardar: vi.fn() },
  smtp: { obtener: vi.fn(), guardar: vi.fn(), probar: vi.fn() },
  identidad: { obtener: vi.fn(), guardar: vi.fn() },
  plantillas: { listar: vi.fn(), guardar: vi.fn(), restablecer: vi.fn(), vistaPrevia: vi.fn() },
}))

const SUPERADMIN = perfil({ permisos: ['*'], es_superadmin: true, rol: null })
const LECTOR = perfil({ permisos: ['configuracion.ver'] })

const PARAMETROS = { max_carreras_aspirante: 5, login_max_intentos: 5, login_bloqueo_minutos: 15 }
const SMTP = { activo: false, host: '', puerto: 587, usuario: '', password_configurada: true, usar_tls: true, usar_ssl: false, remitente: '' }
const ACTIVACION = {
  codigo: 'activacion_cuenta',
  nombre: 'Activación de cuenta',
  descripcion: 'Se envía al registrarse.',
  variables: { nombre: 'Nombre del aspirante', enlace: 'Enlace' },
  asunto: 'Activa tu cuenta',
  cuerpo: 'Hola {{ nombre }}',
}
const IDENTIDAD = { nombre_institucion: 'Universidad de Holguín', color_primario: '#1A3A6B', color_primario_claro: '#2E6DB4', color_acento: '#C8102E', escudo: null }

beforeEach(() => {
  vi.clearAllMocks()
  config.parametros.obtener.mockResolvedValue(PARAMETROS)
  config.smtp.obtener.mockResolvedValue(SMTP)
  config.plantillas.listar.mockResolvedValue([ACTIVACION])
  config.identidad.obtener.mockResolvedValue(IDENTIDAD)
})

async function abrir(usuario = SUPERADMIN) {
  auth.restaurarSesion.mockResolvedValue(usuario)
  renderApp('/admin/configuracion')
  await screen.findByLabelText(/Máximo de carreras/)
}

const pestana = (nombre) => fireEvent.click(screen.getByRole('tab', { name: nombre }))

describe('Parámetros', () => {
  it('valida los límites y guarda', async () => {
    config.parametros.guardar.mockResolvedValue({ ...PARAMETROS, max_carreras_aspirante: 3 })
    await abrir()

    fireEvent.change(screen.getByLabelText(/Máximo de carreras/), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(await screen.findByText('Debe ser un número entre 1 y 10.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Máximo de carreras/), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Los parámetros se guardaron.')).toBeInTheDocument()
    expect(config.parametros.guardar).toHaveBeenCalledWith({ max_carreras_aspirante: '3', login_max_intentos: 5, login_bloqueo_minutos: 15 })
  })

  it('sin ser Superadmin queda en solo lectura', async () => {
    await abrir(LECTOR)

    expect(screen.getByText(/Estás viéndola en modo lectura/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Máximo de carreras/)).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Guardar' })).not.toBeInTheDocument()
  })
})

describe('Correo', () => {
  it('no envía la contraseña si se deja vacía y avisa de que hay una guardada', async () => {
    config.smtp.guardar.mockResolvedValue(SMTP)
    await abrir()
    pestana('Correo')

    expect(await screen.findByText(/Hay una contraseña guardada/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/^Servidor/), { target: { value: 'smtp.uho.edu.cu' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(config.smtp.guardar).toHaveBeenCalled())
    expect(config.smtp.guardar.mock.calls[0][0]).not.toHaveProperty('password')
    expect(config.smtp.guardar.mock.calls[0][0].host).toBe('smtp.uho.edu.cu')
  })

  it('activar exige servidor y remitente', async () => {
    await abrir()
    pestana('Correo')

    fireEvent.click(await screen.findByLabelText(/Usar esta configuración/))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Indica el servidor SMTP.')).toBeInTheDocument()
    expect(config.smtp.guardar).not.toHaveBeenCalled()
  })

  it('envía un correo de prueba', async () => {
    config.smtp.probar.mockResolvedValue({ mensaje: 'Correo de prueba enviado a yo@uho.edu.cu.' })
    await abrir()
    pestana('Correo')

    fireEvent.change(await screen.findByLabelText(/Enviar un correo de prueba/), { target: { value: 'yo@uho.edu.cu' } })
    fireEvent.click(screen.getByRole('button', { name: 'Probar' }))

    expect(await screen.findByText('Correo de prueba enviado a yo@uho.edu.cu.')).toBeInTheDocument()
    expect(config.smtp.probar).toHaveBeenCalledWith('yo@uho.edu.cu')
  })
})

describe('Plantillas', () => {
  it('muestra las variables y rechaza las que no existen', async () => {
    await abrir()
    pestana('Plantillas de correo')

    expect(await screen.findByText('{{ enlace }}')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Cuerpo'), { target: { value: 'Hola {{ ci }}' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Variables no disponibles en esta plantilla: ci.')).toBeInTheDocument()
    expect(config.plantillas.guardar).not.toHaveBeenCalled()
  })

  it('muestra la vista previa', async () => {
    config.plantillas.vistaPrevia.mockResolvedValue({ asunto: 'Activa tu cuenta', cuerpo: 'Hola [Nombre del aspirante]' })
    await abrir()
    pestana('Plantillas de correo')

    fireEvent.click(await screen.findByRole('button', { name: 'Vista previa' }))

    expect(await screen.findByLabelText('Vista previa')).toHaveTextContent('Hola [Nombre del aspirante]')
  })

  it('restablece tras confirmar', async () => {
    config.plantillas.restablecer.mockResolvedValue({ ...ACTIVACION, asunto: 'Texto original' })
    await abrir()
    pestana('Plantillas de correo')

    fireEvent.click(await screen.findByRole('button', { name: 'Restablecer' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Restablecer' }))

    await waitFor(() => expect(screen.getByLabelText('Asunto')).toHaveValue('Texto original'))
    expect(config.plantillas.restablecer).toHaveBeenCalledWith('activacion_cuenta')
  })
})

describe('Identidad visual', () => {
  it('valida los colores y no reenvía el escudo si no cambió', async () => {
    config.identidad.obtener.mockResolvedValue({ ...IDENTIDAD, escudo: 'http://x/media/identidad/e.png' })
    config.identidad.guardar.mockResolvedValue(IDENTIDAD)
    await abrir()
    pestana('Identidad visual')

    fireEvent.change(await screen.findByLabelText(/^Color de acento/), { target: { value: 'rojo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(await screen.findByText(/Usa un color hexadecimal/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/^Color de acento/), { target: { value: '#AA0000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(config.identidad.guardar).toHaveBeenCalled())
    const enviado = config.identidad.guardar.mock.calls[0][0]
    expect(enviado.color_acento).toBe('#AA0000')
    expect(enviado).not.toHaveProperty('escudo')
  })
})

describe('IdentidadProvider', () => {
  it('aplica los colores guardados a las variables CSS', async () => {
    config.obtenerIdentidad.mockResolvedValue({ ...IDENTIDAD, color_primario: '#123456' })
    function Nombre() {
      return useIdentidad().identidad.nombre_institucion
    }
    render(
      <IdentidadProvider>
        <Nombre />
      </IdentidadProvider>,
    )

    await waitFor(() => expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#123456'))
    expect(screen.getByText('Universidad de Holguín')).toBeInTheDocument()
  })

  it('si la API falla mantiene los valores por defecto', async () => {
    config.obtenerIdentidad.mockRejectedValue(new Error('sin red'))
    function Nombre() {
      return useIdentidad().identidad.nombre_institucion
    }
    render(
      <IdentidadProvider>
        <Nombre />
      </IdentidadProvider>,
    )

    expect(await screen.findByText('Universidad de Holguín')).toBeInTheDocument()
  })
})
