import { ChevronDown, ChevronUp, GripVertical } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { cx } from '../../../utils/cx'
import styles from './ListaOrdenable.module.css'

function mover(lista, desde, hasta) {
  const copia = [...lista]
  const [item] = copia.splice(desde, 1)
  copia.splice(hasta, 0, item)
  return copia
}

/**
 * Lista que se reordena arrastrando (drag-and-drop nativo de HTML5), con los
 * botones subir/bajar o con las flechas del teclado sobre el asa. Anuncia
 * cada cambio a los lectores de pantalla.
 *
 * - `items`, `getKey(item)`, `etiqueta(item)`: datos, clave y nombre legible.
 * - `renderItem(item, indice)`: contenido de cada fila.
 * - `onChange(nuevaLista)`: se llama con el orden nuevo.
 * - `acciones(item, indice)`: botones extra por fila (p. ej. quitar).
 */
export function ListaOrdenable({ items, getKey, etiqueta, renderItem, onChange, acciones, disabled = false, label }) {
  const [arrastrado, setArrastrado] = useState(null)
  const [destino, setDestino] = useState(null)
  const [anuncio, setAnuncio] = useState('')
  const asas = useRef(new Map())
  const enfocar = useRef(null)

  // Tras mover con el teclado, el foco sigue al elemento movido.
  useEffect(() => {
    if (enfocar.current == null) return
    asas.current.get(enfocar.current)?.focus()
    enfocar.current = null
  })

  function cambiar(desde, hasta, conFoco = false) {
    if (hasta < 0 || hasta >= items.length || desde === hasta) return
    const item = items[desde]
    if (conFoco) enfocar.current = getKey(item)
    onChange(mover(items, desde, hasta))
    setAnuncio(`${etiqueta(item)}: ahora en la posición ${hasta + 1} de ${items.length}.`)
  }

  function alTeclear(evento, indice) {
    if (evento.key === 'ArrowUp') {
      evento.preventDefault()
      cambiar(indice, indice - 1, true)
    } else if (evento.key === 'ArrowDown') {
      evento.preventDefault()
      cambiar(indice, indice + 1, true)
    }
  }

  function terminar() {
    setArrastrado(null)
    setDestino(null)
  }

  return (
    <>
      <ol className={styles.lista} aria-label={label}>
        {items.map((item, indice) => {
          const clave = getKey(item)
          return (
            <li
              key={clave}
              className={cx(styles.item, arrastrado === indice && styles.arrastrado, destino === indice && arrastrado !== indice && styles.destino)}
              draggable={!disabled}
              onDragStart={(evento) => {
                evento.dataTransfer.effectAllowed = 'move'
                evento.dataTransfer.setData('text/plain', String(clave))
                setArrastrado(indice)
              }}
              onDragOver={(evento) => {
                if (arrastrado == null) return
                evento.preventDefault()
                setDestino(indice)
              }}
              onDrop={(evento) => {
                evento.preventDefault()
                if (arrastrado != null) cambiar(arrastrado, indice)
                terminar()
              }}
              onDragEnd={terminar}
            >
              {!disabled && (
                <button
                  type="button"
                  className={styles.asa}
                  aria-label={`Mover ${etiqueta(item)} (posición ${indice + 1}). Usa las flechas arriba y abajo.`}
                  ref={(nodo) => (nodo ? asas.current.set(clave, nodo) : asas.current.delete(clave))}
                  onKeyDown={(evento) => alTeclear(evento, indice)}
                >
                  <GripVertical aria-hidden="true" />
                </button>
              )}
              <div className={styles.contenido}>{renderItem(item, indice)}</div>
              <div className={styles.acciones}>
                {!disabled && (
                  <>
                    <button
                      type="button"
                      className={styles.flecha}
                      aria-label={`Subir ${etiqueta(item)}`}
                      disabled={indice === 0}
                      onClick={() => cambiar(indice, indice - 1)}
                    >
                      <ChevronUp aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      className={styles.flecha}
                      aria-label={`Bajar ${etiqueta(item)}`}
                      disabled={indice === items.length - 1}
                      onClick={() => cambiar(indice, indice + 1)}
                    >
                      <ChevronDown aria-hidden="true" />
                    </button>
                  </>
                )}
                {acciones?.(item, indice)}
              </div>
            </li>
          )
        })}
      </ol>
      <p className={styles.anuncio} aria-live="polite">
        {anuncio}
      </p>
    </>
  )
}
