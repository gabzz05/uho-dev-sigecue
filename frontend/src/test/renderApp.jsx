import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { ToastProvider } from '../components/ui'
import { AuthProvider } from '../hooks/useAuth'
import { rutas } from '../router'

/** Renderiza la app completa en una ruta, con un router en memoria. */
export function renderApp(ruta = '/') {
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] })
  render(
    <ToastProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ToastProvider>,
  )
  return router
}

export function perfil(extra = {}) {
  return {
    id: 1,
    username: 'jcastro',
    nombre: 'Juan',
    apellidos: 'Castro',
    email: 'jcastro@uho.edu.cu',
    ci: '',
    celular: '',
    foto: null,
    origen: 'local',
    rol: { codigo: 'jefe_ci', nombre: 'Jefe Comisión de Ingreso', ambito: 'global' },
    es_superadmin: false,
    permisos: ['dashboard.ver', 'plan_plazas.ver'],
    ...extra,
  }
}

export const ASPIRANTE = {
  username: 'asp_x',
  nombre: 'María',
  apellidos: 'González',
  email: 'maria@nauta.cu',
  rol: { codigo: 'aspirante', nombre: 'Aspirante', ambito: 'propio' },
  permisos: [],
}
