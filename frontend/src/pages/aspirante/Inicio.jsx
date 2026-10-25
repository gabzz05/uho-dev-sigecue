import { Alert, PageHeader } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'

/** Provisional: el perfil completo y la selección de carreras llegan en feature/portal-aspirante. */
export function InicioAspirante() {
  const { usuario } = useAuth()
  return (
    <>
      <PageHeader title={`Hola, ${usuario.nombre}`} subtitle="Bienvenido(a) al portal del aspirante" />
      <Alert tone="info">
        Pronto podrás completar tu perfil y seleccionar las carreras a las que quieres optar.
      </Alert>
    </>
  )
}
