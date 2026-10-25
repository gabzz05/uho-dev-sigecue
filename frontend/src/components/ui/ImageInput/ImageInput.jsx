import { ImagePlus, Trash2 } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { Button } from '../Button/Button'
import { Field } from '../Form/Field'
import styles from './ImageInput.module.css'

const MAX_MB = 5

/**
 * Selector de imagen con vista previa.
 * `value`: URL existente (string), archivo nuevo (File) o '' para quitarla.
 */
export function ImageInput({ label, value, onChange, error, hint = 'JPG, PNG o WEBP, máximo 5 MB' }) {
  const vistaPrevia = useMemo(() => (value instanceof File ? URL.createObjectURL(value) : value || null), [value])

  useEffect(
    () => () => {
      if (value instanceof File && vistaPrevia) URL.revokeObjectURL(vistaPrevia)
    },
    [value, vistaPrevia],
  )

  const errorTamano = value instanceof File && value.size > MAX_MB * 1024 * 1024 ? `La imagen no puede superar ${MAX_MB} MB.` : ''

  return (
    <Field label={label} hint={hint} error={errorTamano || error}>
      {(a11y) => (
        <div className={styles.contenedor}>
          {vistaPrevia ? (
            <img src={vistaPrevia} alt="Vista previa" className={styles.preview} />
          ) : (
            <span className={styles.vacio} aria-hidden="true">
              <ImagePlus />
            </span>
          )}
          <div className={styles.acciones}>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className={styles.input}
              onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
              {...a11y}
            />
            {vistaPrevia && (
              <Button variant="ghost" size="sm" icon={Trash2} onClick={() => onChange('')}>
                Quitar imagen
              </Button>
            )}
          </div>
        </div>
      )}
    </Field>
  )
}
