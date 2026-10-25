import { Check } from 'lucide-react'
import { Fragment } from 'react'
import { cx } from '../../../utils/cx'
import styles from './Stepper.module.css'

const TEXTO_ESTADO = { completado: 'completado', actual: 'paso actual', pendiente: 'pendiente' }

/**
 * Progreso por pasos. Sirve para el flujo del Plan de Plazas y para los pasos
 * del aspirante. `steps`: `[{ label, estado: 'completado'|'actual'|'pendiente' }]`.
 */
export function Stepper({ steps, label = 'Progreso' }) {
  return (
    <ol className={styles.stepper} aria-label={label}>
      {steps.map((paso, i) => (
        <Fragment key={paso.label}>
          {i > 0 && (
            <li
              aria-hidden="true"
              className={cx(styles.connector, steps[i - 1].estado === 'completado' && styles.connectorDone)}
            />
          )}
          <li className={cx(styles.step, styles[paso.estado])} aria-current={paso.estado === 'actual' ? 'step' : undefined}>
            <span className={styles.circle}>{paso.estado === 'completado' ? <Check aria-hidden="true" /> : i + 1}</span>
            <span className={styles.label}>
              {paso.label}
              <span className={styles.srOnly}> ({TEXTO_ESTADO[paso.estado]})</span>
            </span>
          </li>
        </Fragment>
      ))}
    </ol>
  )
}
