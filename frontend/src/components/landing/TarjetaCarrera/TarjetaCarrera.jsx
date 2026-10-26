import { Clock, GraduationCap, MapPin } from 'lucide-react'
import { Link } from 'react-router'
import { Badge, Button } from '../../ui'
import styles from './TarjetaCarrera.module.css'

/**
 * Tarjeta de la landing (RF-020). Con `oferta` muestra la entidad y el municipio
 * y, si hay convocatoria abierta, el botón "Me interesa". Sin `oferta` es una
 * carrera del catálogo.
 */
export function TarjetaCarrera({ carrera, entidad, onInteres }) {
  return (
    <article className={styles.tarjeta}>
      <div className={styles.imagen}>
        {carrera.imagen ? <img src={carrera.imagen} alt="" loading="lazy" /> : <GraduationCap aria-hidden="true" />}
      </div>
      <div className={styles.cuerpo}>
        {entidad && <Badge tone={entidad.tipo === 'facultad' ? 'info' : 'success'}>{entidad.nombre}</Badge>}
        <h3 className={styles.nombre}>{carrera.nombre}</h3>
        <p className={styles.datos}>
          <span>
            <Clock aria-hidden="true" /> {carrera.duracion_anios} años
          </span>
          {entidad && (
            <span>
              <MapPin aria-hidden="true" /> {entidad.municipio}
            </span>
          )}
        </p>
        {carrera.descripcion && <p className={styles.descripcion}>{carrera.descripcion}</p>}
      </div>
      <footer className={styles.pie}>
        <Button as={Link} to={`/carreras/${carrera.id}`} variant="link" aria-label={`Ver detalle de ${carrera.nombre}`}>
          Ver detalle
        </Button>
        {onInteres && (
          <Button size="sm" aria-label={`Me interesa: ${carrera.nombre}${entidad ? ` en ${entidad.nombre}` : ''}`} onClick={onInteres}>
            Me interesa
          </Button>
        )}
      </footer>
    </article>
  )
}
