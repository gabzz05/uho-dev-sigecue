import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EnConstruccion } from './pages/EnConstruccion'
import * as auth from './services/auth'
import { ASPIRANTE, perfil, renderApp } from './test/renderApp'

vi.mock('./services/auth', () => ({
  restaurarSesion: vi.fn(),
  iniciarSesion: vi.fn(),
  cerrarSesion: vi.fn(),
  registrarAspirante: vi.fn(),
  activarCuenta: vi.fn(),
  pedirRecuperacion: vi.fn(),
  restablecerPassword: vi.fn(),
}))

function errorApi(mensaje, detalles) {
  return { response: { status: 400, data: { error: { codigo: 'invalid', mensaje, detalles } } } }
}

beforeEach(() => {
  vi.clearAllMocks()
  auth.restaurarSesion.mockResolvedValue(null)
})

describe('rutas protegidas', () => {
  it('sin sesión, el panel redirige al login', async () => {
    const router = renderApp('/admin')

    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })

  it('un aspirante que entra al panel va a su portal', async () => {
    auth.restaurarSesion.mockResolvedValue(ASPIRANTE)
    const router = renderApp('/admin')

    expect(await screen.findByRole('navigation', { name: 'Portal del aspirante' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/aspirante')
  })

  it('un interno sin el permiso ve el aviso en lugar del módulo', async () => {
    auth.restaurarSesion.mockResolvedValue(perfil())
    renderApp('/admin/logs')

    expect(await screen.findByText('No tienes permiso para ver esta sección')).toBeInTheDocument()
  })

  it('el sidebar muestra solo los módulos permitidos', async () => {
    auth.restaurarSesion.mockResolvedValue(perfil())
    renderApp('/admin')

    const menu = await screen.findByRole('navigation', { name: 'Menú principal' })
    expect(within(menu).getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: 'Plan de Plazas' })).toBeInTheDocument()
    expect(within(menu).queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
    expect(within(menu).queryByText('Administración')).not.toBeInTheDocument()
  })

  it('el superadmin ve todos los módulos', async () => {
    auth.restaurarSesion.mockResolvedValue(perfil({ permisos: ['*'], es_superadmin: true }))
    renderApp('/admin')

    const menu = await screen.findByRole('navigation', { name: 'Menú principal' })
    expect(within(menu).getByRole('link', { name: 'Logs de auditoría' })).toBeInTheDocument()
  })

  it('un módulo sin pantalla propia muestra "en desarrollo"', () => {
    render(<EnConstruccion titulo="Reportes" />)

    expect(screen.getByText('Módulo en desarrollo')).toBeInTheDocument()
  })

  it('una ruta inexistente muestra 404', async () => {
    renderApp('/no-existe')
    expect(await screen.findByText('Página no encontrada')).toBeInTheDocument()
  })
})

describe('login', () => {
  function llenar(identificador, password) {
    fireEvent.change(screen.getByLabelText(/Correo o usuario/), { target: { value: identificador } })
    fireEvent.change(screen.getByLabelText(/Contraseña/), { target: { value: password } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
  }

  it('valida los campos antes de llamar a la API', async () => {
    renderApp('/login')
    fireEvent.click(await screen.findByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Escribe tu correo o tu usuario.')).toBeInTheDocument()
    expect(auth.iniciarSesion).not.toHaveBeenCalled()
  })

  it('entra y va al panel', async () => {
    auth.iniciarSesion.mockResolvedValue(perfil())
    const router = renderApp('/login')
    await screen.findByRole('button', { name: 'Entrar' })

    llenar('jcastro', 'secreto')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(auth.iniciarSesion).toHaveBeenCalledWith('jcastro', 'secreto')
    expect(router.state.location.pathname).toBe('/admin')
  })

  it('vuelve a la página que pedía antes del login', async () => {
    auth.iniciarSesion.mockResolvedValue(perfil())
    const router = renderApp('/admin/plan-plazas')
    await screen.findByRole('button', { name: 'Entrar' })

    llenar('jcastro', 'secreto')

    await waitFor(() => expect(router.state.location.pathname).toBe('/admin/plan-plazas'))
  })

  it('muestra el mensaje de error de la API', async () => {
    auth.iniciarSesion.mockRejectedValue({
      response: { status: 401, data: { error: { mensaje: 'Usuario o contraseña incorrectos.' } } },
    })
    renderApp('/login')
    await screen.findByRole('button', { name: 'Entrar' })

    llenar('jcastro', 'mal')

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos.')
  })

  it('cerrar sesión vuelve al login', async () => {
    auth.restaurarSesion.mockResolvedValue(perfil())
    auth.cerrarSesion.mockResolvedValue()
    const router = renderApp('/admin')

    fireEvent.click(await screen.findByRole('button', { name: /Juan Castro/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(auth.cerrarSesion).toHaveBeenCalled()
  })
})

describe('registro', () => {
  function completar(datos = {}) {
    const valores = {
      Nombre: 'Carlos',
      Apellidos: 'Martínez',
      'Carnet de identidad': '96071834521',
      Celular: '55987654',
      'Correo electrónico': 'carlos@nauta.cu',
      Contraseña: 'Clave-Segura-1',
      'Repite la contraseña': 'Clave-Segura-1',
      ...datos,
    }
    Object.entries(valores).forEach(([etiqueta, valor]) =>
      fireEvent.change(screen.getByLabelText(new RegExp(`^${etiqueta}`)), { target: { value: valor } }),
    )
  }

  it('valida CI, celular, contraseñas y consentimiento', async () => {
    renderApp('/registro')
    await screen.findByRole('heading', { name: 'Registro de aspirante' })
    completar({ 'Carnet de identidad': '123', Celular: '44123456', 'Repite la contraseña': 'otra' })
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByText(/debe tener 11 dígitos/)).toBeInTheDocument()
    expect(screen.getByText(/empezar por 5/)).toBeInTheDocument()
    expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(screen.getByText(/Debes aceptar la política/)).toBeInTheDocument()
    expect(auth.registrarAspirante).not.toHaveBeenCalled()
  })

  it('envía los datos sin la confirmación y muestra el aviso del correo', async () => {
    auth.registrarAspirante.mockResolvedValue('Te enviamos un correo para activar tu cuenta.')
    renderApp('/registro')
    await screen.findByRole('heading', { name: 'Registro de aspirante' })
    completar()
    fireEvent.click(screen.getByLabelText(/Acepto que mis datos/))
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByText('Te enviamos un correo para activar tu cuenta.')).toBeInTheDocument()
    const enviado = auth.registrarAspirante.mock.calls[0][0]
    expect(enviado).toMatchObject({ ci: '96071834521', acepta_privacidad: true })
    expect(enviado).not.toHaveProperty('confirmacion')
  })

  it('muestra los errores por campo que devuelve la API', async () => {
    auth.registrarAspirante.mockRejectedValue(
      errorApi('Revisa los datos marcados.', { ci: ['Ya existe una cuenta con este carnet de identidad.'] }),
    )
    renderApp('/registro')
    await screen.findByRole('heading', { name: 'Registro de aspirante' })
    completar()
    fireEvent.click(screen.getByLabelText(/Acepto que mis datos/))
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByText('Ya existe una cuenta con este carnet de identidad.')).toBeInTheDocument()
  })
})

describe('recuperación de contraseña', () => {
  it('el login enlaza con la recuperación', async () => {
    renderApp('/login')
    fireEvent.click(await screen.findByRole('link', { name: '¿Olvidaste tu contraseña?' }))
    expect(await screen.findByRole('heading', { name: 'Recuperar contraseña' })).toBeInTheDocument()
  })

  it('pide el enlace y muestra el aviso', async () => {
    auth.pedirRecuperacion.mockResolvedValue('Si el correo pertenece a una cuenta de SIGECUE, te enviamos un enlace.')
    renderApp('/recuperar')
    fireEvent.change(await screen.findByLabelText(/Correo electrónico/), { target: { value: ' ana@nauta.cu ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }))

    expect(await screen.findByText(/te enviamos un enlace/)).toBeInTheDocument()
    expect(auth.pedirRecuperacion).toHaveBeenCalledWith('ana@nauta.cu')
  })

  it('no llama a la API con un correo inválido', async () => {
    renderApp('/recuperar')
    fireEvent.change(await screen.findByLabelText(/Correo electrónico/), { target: { value: 'ana' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }))

    expect(await screen.findByText('Escribe un correo electrónico válido.')).toBeInTheDocument()
    expect(auth.pedirRecuperacion).not.toHaveBeenCalled()
  })

  it('restablece y vuelve al login con el mensaje', async () => {
    auth.restablecerPassword.mockResolvedValue('Tu contraseña se cambió. Ya puedes iniciar sesión con la nueva.')
    renderApp('/restablecer?uid=MQ&token=abc')
    fireEvent.change(await screen.findByLabelText(/Contraseña nueva/), { target: { value: 'Nueva-Clave-1' } })
    fireEvent.change(screen.getByLabelText(/Repite la contraseña/), { target: { value: 'Nueva-Clave-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(await screen.findByText('Tu contraseña se cambió. Ya puedes iniciar sesión con la nueva.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(auth.restablecerPassword).toHaveBeenCalledWith('MQ', 'abc', 'Nueva-Clave-1')
  })

  it('las contraseñas deben coincidir', async () => {
    renderApp('/restablecer?uid=MQ&token=abc')
    fireEvent.change(await screen.findByLabelText(/Contraseña nueva/), { target: { value: 'Nueva-Clave-1' } })
    fireEvent.change(screen.getByLabelText(/Repite la contraseña/), { target: { value: 'Otra-Clave-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(await screen.findByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(auth.restablecerPassword).not.toHaveBeenCalled()
  })

  it('muestra el error del enlace caducado', async () => {
    auth.restablecerPassword.mockRejectedValue(errorApi('El enlace para restablecer la contraseña no es válido o ya caducó. Pide uno nuevo.'))
    renderApp('/restablecer?uid=MQ&token=abc')
    fireEvent.change(await screen.findByLabelText(/Contraseña nueva/), { target: { value: 'Nueva-Clave-1' } })
    fireEvent.change(screen.getByLabelText(/Repite la contraseña/), { target: { value: 'Nueva-Clave-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(await screen.findByText(/ya caducó/)).toBeInTheDocument()
  })

  it('sin uid ni token avisa de enlace inválido', async () => {
    renderApp('/restablecer')
    expect(await screen.findByText('El enlace para restablecer la contraseña no es válido.')).toBeInTheDocument()
  })
})

describe('activación', () => {
  it('activa con el token del enlace', async () => {
    auth.activarCuenta.mockResolvedValue('Tu cuenta está activa. Ya puedes iniciar sesión.')
    renderApp('/activar?token=abc')

    expect(await screen.findByText('Tu cuenta está activa. Ya puedes iniciar sesión.')).toBeInTheDocument()
    expect(auth.activarCuenta).toHaveBeenCalledWith('abc')
  })

  it('sin token avisa de enlace inválido', async () => {
    renderApp('/activar')
    expect(await screen.findByText('El enlace de activación no es válido.')).toBeInTheDocument()
  })
})
