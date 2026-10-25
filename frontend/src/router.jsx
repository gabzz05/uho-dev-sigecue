import { createBrowserRouter } from 'react-router'
import { AdminLayout, AspiranteLayout, MENU_ADMIN, PublicLayout, RequireAuth } from './components/layout'
import { Dashboard } from './pages/admin/Dashboard'
import { InicioAspirante } from './pages/aspirante/Inicio'
import { Activar } from './pages/auth/Activar'
import { Login } from './pages/auth/Login'
import { Registro } from './pages/auth/Registro'
import { MiPerfil } from './pages/cuenta/MiPerfil'
import { EnConstruccion } from './pages/EnConstruccion'
import { NoEncontrado } from './pages/errores/NoEncontrado'
import { InicioPublico } from './pages/public/Inicio'
import { Privacidad } from './pages/public/Privacidad'

// Pantalla de cada entrada del menú. Las que faltan muestran "en construcción"
// hasta que su feature las implemente.
const PANTALLAS_ADMIN = {
  '': <Dashboard />,
}

const rutasAdmin = MENU_ADMIN.flatMap((seccion) => seccion.items).map(({ path, label, permiso }) => ({
  ...(path ? { path } : { index: true }),
  element: <RequireAuth permiso={permiso}>{PANTALLAS_ADMIN[path] ?? <EnConstruccion titulo={label} />}</RequireAuth>,
}))

export const rutas = [
  {
    element: <PublicLayout />,
    children: [
      { index: true, element: <InicioPublico /> },
      { path: 'login', element: <Login /> },
      { path: 'registro', element: <Registro /> },
      { path: 'activar', element: <Activar /> },
      { path: 'privacidad', element: <Privacidad /> },
      { path: '*', element: <NoEncontrado /> },
    ],
  },
  {
    path: 'admin',
    element: (
      <RequireAuth tipo="interno">
        <AdminLayout />
      </RequireAuth>
    ),
    children: [...rutasAdmin, { path: 'perfil', element: <MiPerfil /> }, { path: '*', element: <NoEncontrado /> }],
  },
  {
    path: 'aspirante',
    element: (
      <RequireAuth tipo="aspirante">
        <AspiranteLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <InicioAspirante /> },
      { path: 'perfil', element: <MiPerfil /> },
      { path: '*', element: <NoEncontrado /> },
    ],
  },
]

export const router = createBrowserRouter(rutas)
