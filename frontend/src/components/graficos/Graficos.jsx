import { useId, useState } from 'react'
import { VisuallyHidden } from '../ui'
import styles from './Graficos.module.css'

const numero = (n) => (n ?? 0).toLocaleString('es-CU')

/**
 * Termómetro (RF-053): solicitudes frente a las plazas del plan, una fila por carrera y entidad.
 * La barra llena la proporción solicitudes/plazas; la marca vertical es el 100 % del plan.
 * Más demanda que plazas se ve como barra que pasa la marca.
 * `filas`: `[{ clave, etiqueta, detalle?, valor, referencia }]`.
 */
export function Termometro({ filas, titulo, unidad = 'solicitudes', referenciaNombre = 'plazas' }) {
  // Escala común: el máximo entre demanda y plazas, para comparar filas entre sí.
  const maximo = Math.max(1, ...filas.map((f) => Math.max(f.valor, f.referencia ?? 0)))
  return (
    <figure className={styles.figura}>
      {titulo && <figcaption className={styles.titulo}>{titulo}</figcaption>}
      <ul className={styles.filas}>
        {filas.map((f) => {
          const porcentaje = f.referencia ? Math.round((f.valor / f.referencia) * 100) : null
          const texto = `${numero(f.valor)} ${unidad} de ${numero(f.referencia)} ${referenciaNombre}${porcentaje != null ? ` (${porcentaje} %)` : ''}`
          return (
            <li key={f.clave} className={styles.fila} title={`${f.etiqueta}: ${texto}`}>
              <span className={styles.etiqueta}>
                {f.etiqueta}
                {f.detalle && <span className={styles.detalle}>{f.detalle}</span>}
              </span>
              <span className={styles.pista} aria-hidden="true">
                <span className={styles.relleno} style={{ width: `${(f.valor / maximo) * 100}%` }} />
                {f.referencia > 0 && <span className={styles.referencia} style={{ left: `${(f.referencia / maximo) * 100}%` }} />}
              </span>
              <span className={styles.valor}>
                <strong>{numero(f.valor)}</strong> / {numero(f.referencia)}
                {porcentaje != null && <span className={styles.detalle}>{porcentaje} %</span>}
                <VisuallyHidden>{texto}</VisuallyHidden>
              </span>
            </li>
          )
        })}
      </ul>
      <p className={styles.leyenda}>
        <span className={styles.muestraRelleno} aria-hidden="true" /> {unidad}
        <span className={styles.muestraReferencia} aria-hidden="true" /> {referenciaNombre} del plan
      </p>
    </figure>
  )
}

/** Barras horizontales de una sola serie (distribución). `filas`: `[{ clave, etiqueta, valor }]`. */
export function BarrasHorizontales({ filas, titulo, unidad }) {
  const maximo = Math.max(1, ...filas.map((f) => f.valor))
  return (
    <figure className={styles.figura}>
      {titulo && <figcaption className={styles.titulo}>{titulo}</figcaption>}
      <ul className={styles.filas}>
        {filas.map((f) => (
          <li key={f.clave} className={styles.fila} title={`${f.etiqueta}: ${numero(f.valor)} ${unidad}`}>
            <span className={styles.etiqueta}>{f.etiqueta}</span>
            <span className={styles.pista} aria-hidden="true">
              <span className={styles.relleno} style={{ width: `${(f.valor / maximo) * 100}%` }} />
            </span>
            <span className={styles.valor}>
              <strong>{numero(f.valor)}</strong>
              <VisuallyHidden> {unidad}</VisuallyHidden>
            </span>
          </li>
        ))}
      </ul>
    </figure>
  )
}

const ALTO = 160
const MARGEN = { arriba: 12, abajo: 24, izquierda: 32 }

/**
 * Evolución diaria (columnas por día) en SVG, con tooltip al pasar el cursor
 * o enfocar con el teclado, y la tabla de valores para lectores de pantalla.
 * `puntos`: `[{ dia: 'AAAA-MM-DD', total }]`.
 */
export function EvolucionDiaria({ puntos, titulo, unidad = 'solicitudes' }) {
  const [activo, setActivo] = useState(null)
  const idTabla = useId()
  const maximo = Math.max(1, ...puntos.map((p) => p.total))
  const ancho = Math.max(320, puntos.length * 28 + MARGEN.izquierda)
  const paso = (ancho - MARGEN.izquierda) / Math.max(puntos.length, 1)
  const barra = Math.max(4, Math.min(20, paso - 6))
  const y = (valor) => MARGEN.arriba + (ALTO - MARGEN.arriba - MARGEN.abajo) * (1 - valor / maximo)
  const base = ALTO - MARGEN.abajo
  const fecha = (dia) => `${dia.slice(8, 10)}/${dia.slice(5, 7)}`
  // Etiquetas del eje X selectivas: como mucho unas 8, para que no se solapen.
  const cadaCuantos = Math.ceil(puntos.length / 8)

  return (
    <figure className={styles.figura}>
      {titulo && <figcaption className={styles.titulo}>{titulo}</figcaption>}
      <div className={styles.lienzo}>
        <svg viewBox={`0 0 ${ancho} ${ALTO}`} width="100%" height={ALTO} role="img" aria-label={titulo} aria-describedby={idTabla} className={styles.svg}>
          {[0, 0.5, 1].map((t) => (
            <g key={t}>
              <line x1={MARGEN.izquierda} x2={ancho} y1={y(maximo * t)} y2={y(maximo * t)} className={styles.rejilla} />
              <text x={MARGEN.izquierda - 6} y={y(maximo * t) + 4} textAnchor="end" className={styles.eje}>
                {Math.round(maximo * t)}
              </text>
            </g>
          ))}
          {puntos.map((p, i) => {
            const x = MARGEN.izquierda + paso * i + (paso - barra) / 2
            const alto = Math.max(base - y(p.total), p.total > 0 ? 2 : 0)
            return (
              <g
                key={p.dia}
                tabIndex={0}
                className={styles.columna}
                onMouseEnter={() => setActivo(i)}
                onMouseLeave={() => setActivo(null)}
                onFocus={() => setActivo(i)}
                onBlur={() => setActivo(null)}
                aria-label={`${fecha(p.dia)}: ${p.total} ${unidad}`}
              >
                {/* Zona sensible más grande que la marca. */}
                <rect x={MARGEN.izquierda + paso * i} y={MARGEN.arriba} width={paso} height={base - MARGEN.arriba} fill="transparent" />
                <path d={columnaRedondeada(x, base - alto, barra, alto)} className={activo === i ? styles.barraActiva : styles.barra} />
                {i % cadaCuantos === 0 && (
                  <text x={x + barra / 2} y={ALTO - 6} textAnchor="middle" className={styles.eje}>
                    {fecha(p.dia)}
                  </text>
                )}
              </g>
            )
          })}
          <line x1={MARGEN.izquierda} x2={ancho} y1={base} y2={base} className={styles.base} />
        </svg>
        {activo != null && (
          <div className={styles.tooltip} style={{ left: `${((MARGEN.izquierda + paso * (activo + 0.5)) / ancho) * 100}%` }} role="status">
            <strong>{puntos[activo].total}</strong> {unidad}
            <span>{fecha(puntos[activo].dia)}</span>
          </div>
        )}
      </div>
      <table id={idTabla} className={styles.tablaOculta}>
        <caption>{titulo}</caption>
        <thead>
          <tr>
            <th scope="col">Día</th>
            <th scope="col">{unidad}</th>
          </tr>
        </thead>
        <tbody>
          {puntos.map((p) => (
            <tr key={p.dia}>
              <td>{fecha(p.dia)}</td>
              <td>{p.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

/** Columna con las esquinas superiores redondeadas (4 px) y la base recta sobre el eje. */
function columnaRedondeada(x, y, ancho, alto) {
  if (alto <= 0) return ''
  const r = Math.min(4, ancho / 2, alto)
  return `M${x},${y + alto} V${y + r} Q${x},${y} ${x + r},${y} H${x + ancho - r} Q${x + ancho},${y} ${x + ancho},${y + r} V${y + alto} Z`
}
