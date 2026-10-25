import { RouterProvider } from 'react-router'
import { ToastProvider } from './components/ui'
import { AuthProvider } from './hooks/useAuth'
import { router } from './router'

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ToastProvider>
  )
}

export default App
