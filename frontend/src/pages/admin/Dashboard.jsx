import { Alert, PageHeader } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'

/** Provisional: los KPIs y gráficos llegan en feature/dashboard. */
export function Dashboard() {
  const { usuario } = useAuth()
  return (
    <>
      <PageHeader title="Dashboard" subtitle={`Bienvenido(a), ${usuario.nombre || usuario.username}`} />
      <Alert tone="info" title="Panel en construcción">
        Los indicadores del proceso de ingreso se mostrarán aquí a medida que se habiliten los módulos.
      </Alert>
    </>
  )
}
