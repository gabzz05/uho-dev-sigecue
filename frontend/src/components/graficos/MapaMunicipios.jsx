import { cx } from '../../utils/cx'
import styles from './MapaMunicipios.module.css'

/**
 * Posición aproximada de cada municipio de Holguín (columna, fila), de oeste a
 * este y de norte a sur. Es un mapa PROVISIONAL de casillas mientras no llegue
 * la geometría oficial (ver docs/ANOTACIONES.md, sección 1): para usar el
 * GeoJSON basta con otra implementación que reciba las mismas `filas`.
 */
const POSICIONES = {
  Gibara: [2, 1],
  'Rafael Freyre': [3, 1],
  Banes: [4, 1],
  Antilla: [5, 1],
  'Calixto García': [1, 2],
  Holguín: [2, 2],
  Báguanos: [3, 2],
  Cueto: [4, 2],
  Mayarí: [5, 2],
  'Frank País': [6, 2],
  Moa: [7, 2],
  Cacocum: [2, 3],
  'Urbano Noris': [3, 3],
  'Sagua de Tánamo': [6, 3],
}

// Escala secuencial de un solo tono (claro → oscuro): 0 tiene su propio color "sin interés".
const NIVELES = 5

function nivel(valor, maximo) {
  if (!valor) return 0
  return Math.max(1, Math.ceil((valor / maximo) * NIVELES))
}

/**
 * Distribución territorial (RF-029): una casilla por municipio, más intensa
 * cuanto más interés. El número va siempre escrito (no depende solo del color)
 * y debajo hay una tabla con los mismos datos.
 * `filas`: `[{ municipio, nombre, total }]`.
 */
export function MapaMunicipios({ filas, titulo, unidad = 'expresiones de interés' }) {
  const maximo = Math.max(1, ...filas.map((f) => f.total))
  const ordenadas = [...filas].sort((a, b) => b.total - a.total || a.nombre.localeCompare(b.nombre))

  return (
    <figure className={styles.figura}>
      {titulo && <figcaption className={styles.titulo}>{titulo}</figcaption>}
      <div className={styles.mapa} role="img" aria-label={`${titulo ?? 'Mapa'}: ${ordenadas.map((f) => `${f.nombre} ${f.total}`).join(', ')}`}>
        {filas.map((f) => {
          const [columna, fila] = POSICIONES[f.nombre] ?? []
          const n = nivel(f.total, maximo)
          return (
            <div
              key={f.municipio}
              className={cx(styles.casilla, styles[`n${n}`])}
              style={columna ? { gridColumn: columna, gridRow: fila } : undefined}
              title={`${f.nombre}: ${f.total} ${unidad}`}
            >
              <span className={styles.nombre}>{f.nombre}</span>
              <strong className={styles.valor}>{f.total}</strong>
            </div>
          )
        })}
      </div>
      <p className={styles.leyenda} aria-hidden="true">
        <span>Menos</span>
        {Array.from({ length: NIVELES + 1 }, (_, i) => (
          <span key={i} className={cx(styles.muestra, styles[`n${i}`])} />
        ))}
        <span>Más</span>
      </p>
      <p className={styles.nota}>Mapa provisional: cada casilla es un municipio en su posición aproximada. El interés se cuenta por el municipio de la entidad que oferta la carrera.</p>
      <div className={styles.tablaContenedor}>
        <table className={styles.tabla}>
          <thead>
            <tr>
              <th scope="col">Municipio</th>
              <th scope="col" className={styles.numero}>
                {unidad}
              </th>
            </tr>
          </thead>
          <tbody>
            {ordenadas.map((f) => (
              <tr key={f.municipio}>
                <td>{f.nombre}</td>
                <td className={styles.numero}>{f.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  )
}
