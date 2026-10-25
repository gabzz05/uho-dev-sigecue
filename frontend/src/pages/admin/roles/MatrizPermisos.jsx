import styles from './MatrizPermisos.module.css'

const ACCIONES = [
  { id: 'ver', label: 'Ver' },
  { id: 'crear', label: 'Crear' },
  { id: 'editar', label: 'Editar' },
  { id: 'eliminar', label: 'Eliminar' },
  { id: 'exportar', label: 'Exportar' },
]

/**
 * Matriz módulo × acción para asignar permisos a un rol (RE-006).
 * `catalogo`: respuesta de `/admin/roles/catalogo/`. `value`: códigos `modulo.accion`.
 */
export function MatrizPermisos({ catalogo, value = [], onChange, disabled = false, error }) {
  const marcados = new Set(value)

  function alternar(codigo) {
    const siguiente = new Set(marcados)
    if (siguiente.has(codigo)) siguiente.delete(codigo)
    else siguiente.add(codigo)
    onChange([...siguiente].sort())
  }

  function alternarModulo(modulo) {
    const codigos = modulo.acciones.map((a) => a.codigo)
    const todos = codigos.every((c) => marcados.has(c))
    const siguiente = new Set(marcados)
    codigos.forEach((c) => (todos ? siguiente.delete(c) : siguiente.add(c)))
    onChange([...siguiente].sort())
  }

  return (
    <fieldset className={styles.fieldset} aria-describedby={error ? 'permisos-error' : undefined}>
      <legend className={styles.legend}>Permisos</legend>
      <div className={styles.wrapper}>
        <table className={styles.tabla}>
          <thead>
            <tr>
              <th scope="col">Módulo</th>
              <th scope="col">Todos</th>
              {ACCIONES.map((a) => (
                <th key={a.id} scope="col">
                  {a.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {catalogo.map((modulo) => {
              const porAccion = Object.fromEntries(modulo.acciones.map((a) => [a.accion, a.codigo]))
              const todos = modulo.acciones.every((a) => marcados.has(a.codigo))
              return (
                <tr key={modulo.modulo}>
                  <th scope="row">{modulo.nombre}</th>
                  <td>
                    <input
                      type="checkbox"
                      checked={todos}
                      disabled={disabled}
                      onChange={() => alternarModulo(modulo)}
                      aria-label={`Todos los permisos de ${modulo.nombre}`}
                    />
                  </td>
                  {ACCIONES.map((a) => (
                    <td key={a.id}>
                      {porAccion[a.id] ? (
                        <input
                          type="checkbox"
                          checked={marcados.has(porAccion[a.id])}
                          disabled={disabled}
                          onChange={() => alternar(porAccion[a.id])}
                          aria-label={`${a.label} en ${modulo.nombre}`}
                        />
                      ) : (
                        <span className={styles.na} aria-hidden="true">
                          —
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {error && (
        <p id="permisos-error" className={styles.error}>
          {error}
        </p>
      )}
    </fieldset>
  )
}
