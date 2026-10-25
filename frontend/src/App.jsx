import { RouterProvider } from 'react-router'
import { ToastProvider } from './components/ui'
import { AuthProvider } from './hooks/useAuth'
import { IdentidadProvider } from './hooks/useIdentidad'
import { router } from './router'

function App() {
  return (
    <IdentidadProvider>
      <ToastProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ToastProvider>
    </IdentidadProvider>
  )
}

export default App
