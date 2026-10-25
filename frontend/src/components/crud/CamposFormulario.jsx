import { cx } from '../../utils/cx'
import { Checkbox, ImageInput, Input, Select, Textarea } from '../ui'
import styles from './Crud.module.css'

/**
 * Pinta los campos de un formulario a partir de un esquema:
 * `[{ name, label, type, required, hint, options, disabled, ancho: 'mitad' }]`.
 * Tipos: text, email, tel, number, password, textarea, select, checkbox, image
 * y `custom` (con `render({ value, onChange, error })`).
 * `campos` también puede ser una función de los valores actuales, para
 * mostrar u ocultar campos según lo que el usuario va eligiendo.
 */
export function CamposFormulario({ campos, formulario }) {
  const { campo, checkbox, valores, setValores, errores } = formulario
  const lista = typeof campos === 'function' ? campos(valores) : campos
  const asignar = (nombre) => (valor) => setValores((v) => ({ ...v, [nombre]: valor }))

  return (
    <div className={styles.campos}>
      {lista.map((def) => {
        const clase = def.ancho === 'mitad' ? styles.mitad : styles.completo
        const comunes = { label: def.label, required: def.required, hint: def.hint, disabled: def.disabled, className: clase }

        switch (def.type) {
          case 'image':
            return (
              <div key={def.name} className={clase}>
                <ImageInput label={def.label} value={valores[def.name]} error={errores[def.name]} onChange={asignar(def.name)} />
              </div>
            )
          case 'custom':
            return (
              <div key={def.name} className={clase}>
                {def.render({ value: valores[def.name], onChange: asignar(def.name), error: errores[def.name] })}
              </div>
            )
          case 'checkbox':
            return <Checkbox key={def.name} label={def.label} disabled={def.disabled} className={clase} {...checkbox(def.name)} />
          case 'textarea':
            return <Textarea key={def.name} {...comunes} rows={def.rows ?? 3} {...campo(def.name)} />
          case 'select':
            return (
              <Select
                key={def.name}
                {...comunes}
                options={def.options}
                placeholder={def.placeholder ?? 'Selecciona…'}
                {...campo(def.name)}
              />
            )
          default:
            return (
              <Input
                key={def.name}
                {...comunes}
                className={cx(clase)}
                type={def.type ?? 'text'}
                min={def.min}
                max={def.max}
                autoComplete={def.autoComplete}
                {...campo(def.name)}
              />
            )
        }
      })}
    </div>
  )
}
