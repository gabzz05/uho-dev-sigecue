import styles from './CheckboxGroup.module.css'

/** Varias casillas con una leyenda común. `value`: lista de valores marcados. */
export function CheckboxGroup({ legend, hint, options, value = [], onChange, error }) {
  const marcados = new Set(value)

  function alternar(opcion) {
    const siguiente = new Set(marcados)
    if (siguiente.has(opcion)) siguiente.delete(opcion)
    else siguiente.add(opcion)
    onChange([...siguiente])
  }

  return (
    <fieldset className={styles.grupo}>
      <legend className={styles.legend}>{legend}</legend>
      {hint && <p className={styles.hint}>{hint}</p>}
      <div className={styles.opciones}>
        {options.map((o) => (
          <label key={o.value} className={styles.opcion}>
            <input type="checkbox" checked={marcados.has(o.value)} onChange={() => alternar(o.value)} />
            {o.label}
          </label>
        ))}
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </fieldset>
  )
}
