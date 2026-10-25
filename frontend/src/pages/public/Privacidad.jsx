import { Alert, Card, CardBody, PageHeader } from '../../components/ui'
import styles from './Privacidad.module.css'

/** Política de privacidad accesible antes del registro (RG-026). El texto oficial lo aporta la UHO. */
export function Privacidad() {
  return (
    <div className={styles.page}>
      <PageHeader title="Política de Privacidad" subtitle="Universidad de Holguín — SIGECUE" />
      <Card>
        <CardBody>
          <Alert tone="warning" title="Texto pendiente">
            El texto oficial de la política de privacidad de la UHO se incorporará aquí. Ver docs/ANOTACIONES.md.
          </Alert>
        </CardBody>
      </Card>
    </div>
  )
}
