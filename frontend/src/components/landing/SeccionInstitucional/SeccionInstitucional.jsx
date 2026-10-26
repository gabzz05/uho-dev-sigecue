import { Mail, MapPin, Phone } from 'lucide-react'
import { useIdentidad } from '../../../hooks/useIdentidad'
import styles from './SeccionInstitucional.module.css'

/**
 * Misión, visión y contacto de la universidad (RF-025).
 * Textos provisionales: la UHO aportará los oficiales (ver docs/ANOTACIONES.md).
 */
const TEXTOS = {
  mision: 'Formar profesionales competentes y comprometidos con el desarrollo de la provincia y del país.',
  vision: 'Ser una universidad de excelencia, reconocida por la calidad de sus egresados y su vínculo con la sociedad.',
  direccion: 'Holguín, Cuba',
  telefono: 'Pendiente',
  email: 'Pendiente',
}

export function SeccionInstitucional() {
  const { identidad } = useIdentidad()
  return (
    <section className={styles.seccion} aria-labelledby="titulo-institucional">
      <h2 id="titulo-institucional" className={styles.titulo}>
        {identidad.nombre_institucion}
      </h2>
      <div className={styles.columnas}>
        <div>
          <h3>Misión</h3>
          <p>{TEXTOS.mision}</p>
        </div>
        <div>
          <h3>Visión</h3>
          <p>{TEXTOS.vision}</p>
        </div>
        <div>
          <h3>Contacto</h3>
          <ul className={styles.contacto}>
            <li>
              <MapPin aria-hidden="true" /> {TEXTOS.direccion}
            </li>
            <li>
              <Phone aria-hidden="true" /> {TEXTOS.telefono}
            </li>
            <li>
              <Mail aria-hidden="true" /> {TEXTOS.email}
            </li>
          </ul>
        </div>
      </div>
    </section>
  )
}
