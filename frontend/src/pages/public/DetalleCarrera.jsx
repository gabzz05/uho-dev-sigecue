import { ArrowLeft, Clock, GraduationCap, MapPin } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router'
import { FormularioInteres } from '../../components/landing/FormularioInteres/FormularioInteres'
import { Alert, Badge, Button, Card, CardBody, Spinner } from '../../components/ui'
import { useCarga } from '../../hooks/useCarga'
import { publico } from '../../services/publico'
import styles from './DetalleCarrera.module.css'

const SECCIONES = [
  ['descripcion', 'Descripción'],
  ['objetivo', 'Objetivo'],
  ['perfil_egresado', 'Perfil del egresado'],
  ['requisitos', 'Requisitos de ingreso'],
]

/** Página de una carrera (sección 9.1): información completa y dónde se oferta. */
export function DetalleCarrera() {
  const { id } = useParams()
  const carrera = useCarga(useCallback(() => publico.carrera(id), [id]))
  const convocatoria = useCarga(publico.convocatoriaInteres)
  const [interes, setInteres] = useState(null)

  if (carrera.cargando || convocatoria.cargando) {
    return (
      <div className={styles.pagina}>
        <Spinner label="Cargando la carrera" />
      </div>
    )
  }
  if (carrera.error) {
    return (
      <div className={styles.pagina}>
        <Alert tone="danger">{carrera.error}</Alert>
      </div>
    )
  }

  const c = carrera.datos
  return (
    <div className={styles.pagina}>
      <Button as={Link} to="/#carreras" variant="link" icon={ArrowLeft}>
        Volver a las carreras
      </Button>

      <header className={styles.cabecera}>
        <div className={styles.imagen}>
          {c.imagen ? <img src={c.imagen} alt="" /> : <GraduationCap aria-hidden="true" />}
        </div>
        <div>
          <h1 className={styles.titulo}>{c.nombre}</h1>
          <p className={styles.dato}>
            <Clock aria-hidden="true" /> {c.duracion_anios} años · Modalidad por encuentro
          </p>
        </div>
      </header>

      <div className={styles.columnas}>
        <Card>
          <CardBody>
            {SECCIONES.filter(([campo]) => c[campo]).map(([campo, titulo]) => (
              <section key={campo} className={styles.seccion}>
                <h2>{titulo}</h2>
                <p>{c[campo]}</p>
              </section>
            ))}
          </CardBody>
        </Card>

        <aside>
          <Card>
            <CardBody>
              <h2 className={styles.asideTitulo}>Dónde se oferta</h2>
              {c.ofertas.length === 0 ? (
                <p className={styles.nota}>
                  {convocatoria.datos
                    ? 'Esta carrera no está en la oferta de la convocatoria actual.'
                    : 'Ahora no hay una convocatoria de interés abierta. Vuelve pronto.'}
                </p>
              ) : (
                <ul className={styles.ofertas}>
                  {c.ofertas.map((oferta) => (
                    <li key={oferta.id}>
                      <div>
                        <Badge tone={oferta.entidad.tipo === 'facultad' ? 'info' : 'success'}>{oferta.entidad.nombre}</Badge>
                        <span className={styles.dato}>
                          <MapPin aria-hidden="true" /> {oferta.entidad.municipio}
                        </span>
                      </div>
                      <Button size="sm" aria-label={`Me interesa en ${oferta.entidad.nombre}`} onClick={() => setInteres({ ...oferta, carrera: c })}>
                        Me interesa
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </aside>
      </div>

      {interes && <FormularioInteres oferta={interes} convocatoria={convocatoria.datos} onClose={() => setInteres(null)} />}
    </div>
  )
}
