import { useId, useRef } from 'react'
import { cx } from '../../../utils/cx'
import styles from './Tabs.module.css'

/**
 * Pestañas accesibles (patrón WAI-ARIA: flechas para moverse entre pestañas).
 * `tabs`: `[{ id, label }]`; `children` es el contenido de la pestaña activa.
 */
export function Tabs({ tabs, activa, onChange, label, children }) {
  const baseId = useId()
  const refs = useRef({})

  function alTeclear(evento, indice) {
    const desplazamiento = { ArrowRight: 1, ArrowLeft: -1 }[evento.key]
    if (!desplazamiento) return
    const siguiente = tabs[(indice + desplazamiento + tabs.length) % tabs.length]
    onChange(siguiente.id)
    refs.current[siguiente.id]?.focus()
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className={styles.lista}>
        {tabs.map((tab, i) => {
          const seleccionada = tab.id === activa
          return (
            <button
              key={tab.id}
              ref={(el) => (refs.current[tab.id] = el)}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tab.id}`}
              aria-selected={seleccionada}
              aria-controls={`${baseId}-panel`}
              tabIndex={seleccionada ? 0 : -1}
              className={cx(styles.tab, seleccionada && styles.activa)}
              onClick={() => onChange(tab.id)}
              onKeyDown={(e) => alTeclear(e, i)}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
      <div role="tabpanel" id={`${baseId}-panel`} aria-labelledby={`${baseId}-tab-${activa}`} className={styles.panel}>
        {children}
      </div>
    </div>
  )
}
