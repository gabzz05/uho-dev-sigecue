import { Construction } from 'lucide-react'
import { Card, CardBody, EmptyState, PageHeader } from '../components/ui'

/** Destino provisional de los módulos que todavía no se implementaron. */
export function EnConstruccion({ titulo }) {
  return (
    <>
      <PageHeader title={titulo} />
      <Card>
        <CardBody>
          <EmptyState icon={Construction} title="Módulo en desarrollo" message="Esta sección estará disponible próximamente." />
        </CardBody>
      </Card>
    </>
  )
}
