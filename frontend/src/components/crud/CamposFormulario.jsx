import { ImageInput, Input, Select, Textarea } from '../ui'
import { cx } from '../../utils/cx'
import styles from './Crud.module.css'

/**
 * Pinta los campos de un formulario a partir de un esquema:
 * `[{ name, label, type, required, hint, options, ancho: 'mitad' }]`.
 * Tipos: text, email, tel, number, textarea, select, image.
 */
export function CamposFormulario({ campos, formulario }) {
  const { campo, valores, setValores, errores } = formulario

  return (
    <div className={styles.campos}>
      {campos.map((def) => {
        const clase = cx(def.ancho === 'mitad' ? styles.mitad : styles.completo)
        const comunes = { label: def.label, required: def.required, hint: def.hint, className: clase }

        if (def.type === 'image') {
          return (
            <div key={def.name} className={clase}>
              <ImageInput
                label={def.label}
                value={valores[def.name]}
                error={errores[def.name]}
                onChange={(valor) => setValores((v) => ({ ...v, [def.name]: valor }))}
              />
            </div>
          )
        }
        if (def.type === 'textarea') {
          return <Textarea key={def.name} {...comunes} rows={def.rows ?? 3} {...campo(def.name)} />
        }
        if (def.type === 'select') {
          return (
            <Select
              key={def.name}
              {...comunes}
              options={def.options}
              placeholder={def.placeholder ?? 'Selecciona…'}
              {...campo(def.name)}
            />
          )
        }
        return <Input key={def.name} {...comunes} type={def.type ?? 'text'} min={def.min} max={def.max} {...campo(def.name)} />
      })}
    </div>
  )
}
