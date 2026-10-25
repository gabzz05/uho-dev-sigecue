import { useId } from 'react'
import { cx } from '../../../utils/cx'
import { Field } from './Field'
import styles from './Form.module.css'

export function Input({ label, hint, error, required, className, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} required={required} className={className}>
      {(a11y) => <input className={cx(styles.control, error && styles.invalid)} {...a11y} {...props} />}
    </Field>
  )
}

export function Textarea({ label, hint, error, required, className, rows = 4, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} required={required} className={className}>
      {(a11y) => (
        <textarea className={cx(styles.control, styles.textarea, error && styles.invalid)} rows={rows} {...a11y} {...props} />
      )}
    </Field>
  )
}

/** `options`: `[{ value, label }]`. `placeholder` añade una primera opción vacía. */
export function Select({ label, hint, error, required, className, options = [], placeholder, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} required={required} className={className}>
      {(a11y) => (
        <select className={cx(styles.control, styles.select, error && styles.invalid)} {...a11y} {...props}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((opcion) => (
            <option key={opcion.value} value={opcion.value}>
              {opcion.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  )
}

export function Checkbox({ label, error, className, ...props }) {
  const id = useId()
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className={cx(styles.checkboxField, className)}>
      <div className={styles.checkboxRow}>
        <input
          id={id}
          type="checkbox"
          className={styles.checkbox}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          {...props}
        />
        <label htmlFor={id} className={styles.checkboxLabel}>
          {label}
        </label>
      </div>
      {error && (
        <p id={errorId} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  )
}
