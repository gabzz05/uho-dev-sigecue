import { MapPinOff } from 'lucide-react'
import { Link } from 'react-router'
import { Button, EmptyState } from '../../components/ui'
import styles from './NoEncontrado.module.css'

export function NoEncontrado() {
  return (
    <div className={styles.page}>
      <EmptyState
        icon={MapPinOff}
        title="Página no encontrada"
        message="La dirección que buscas no existe o fue movida."
        action={
          <Button as={Link} to="/">
            Ir al inicio
          </Button>
        }
      />
    </div>
  )
}
