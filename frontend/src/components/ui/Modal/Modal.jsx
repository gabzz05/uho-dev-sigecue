import { X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { cx } from '../../../utils/cx'
import styles from './Modal.module.css'

const ENFOCABLES = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

/**
 * Diálogo modal accesible: se cierra con Escape o clic fuera, mantiene el foco
 * dentro mientras está abierto y lo devuelve al elemento que lo abrió.
 */
export function Modal({ open, onClose, title, eyebrow, description, footer, size = 'md', children }) {
  const panelRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const titleId = useId()

  // Con un `onClose` inline el efecto no debe reejecutarse en cada render:
  // movería el foco al primer campo mientras el usuario escribe.
  useEffect(() => {
    onCloseRef.current = onClose
  })

  useEffect(() => {
    if (!open) return undefined
    const anterior = document.activeElement
    const panel = panelRef.current
    panel?.querySelector(ENFOCABLES)?.focus()

    function alTeclear(evento) {
      if (evento.key === 'Escape') {
        onCloseRef.current()
        return
      }
      if (evento.key !== 'Tab' || !panel) return
      const enfocables = [...panel.querySelectorAll(ENFOCABLES)].filter((el) => !el.disabled)
      if (enfocables.length === 0) return
      const primero = enfocables[0]
      const ultimo = enfocables[enfocables.length - 1]
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault()
        ultimo.focus()
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault()
        primero.focus()
      }
    }

    document.addEventListener('keydown', alTeclear)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', alTeclear)
      document.body.style.overflow = ''
      anterior?.focus?.()
    }
  }, [open])

  if (!open) return null

  return createPortal(
    <div className={styles.overlay} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={panelRef}
        className={cx(styles.panel, styles[size])}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className={styles.header}>
          {eyebrow && <span className={styles.eyebrow}>{eyebrow}</span>}
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          {description && <p className={styles.description}>{description}</p>}
          <button type="button" className={styles.close} onClick={onClose} aria-label="Cerrar">
            <X aria-hidden="true" />
          </button>
        </header>
        <div className={styles.body}>{children}</div>
        {footer && <footer className={styles.footer}>{footer}</footer>}
      </div>
    </div>,
    document.body,
  )
}
