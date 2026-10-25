import { Link } from 'react-router'
import { Button } from '../../components/ui'
import styles from './Inicio.module.css'

/** Provisional: el catálogo de carreras y la expresión de interés llegan en feature/landing-interes. */
export function InicioPublico() {
  return (
    <section className={styles.hero}>
      <h1 className={styles.title}>Carreras por Encuentro</h1>
      <p className={styles.text}>
        Estudia en la modalidad que se adapta a tu vida. Consulta la oferta de las Facultades y de los Centros
        Universitarios de tu municipio.
      </p>
      <div className={styles.actions}>
        <Button as={Link} to="/registro" variant="inverse" size="lg">
          Crear cuenta de aspirante
        </Button>
        <Button as={Link} to="/login" variant="outline" size="lg" className={styles.ghost}>
          Iniciar sesión
        </Button>
      </div>
      <span id="carreras" />
    </section>
  )
}
