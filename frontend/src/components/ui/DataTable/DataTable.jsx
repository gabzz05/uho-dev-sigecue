import { cx } from '../../../utils/cx'
import { EmptyState } from '../EmptyState/EmptyState'
import { Spinner } from '../Spinner/Spinner'
import styles from './DataTable.module.css'

/**
 * Tabla de datos.
 * `columns`: `[{ key, header, render?: (fila) => node, align?: 'left'|'center'|'right' }]`.
 * En pantallas estrechas se desplaza horizontalmente dentro de su contenedor.
 */
export function DataTable({
  columns,
  rows,
  rowKey = 'id',
  loading = false,
  caption,
  emptyMessage = 'No hay registros para mostrar.',
  rowClassName,
}) {
  const claveDe = typeof rowKey === 'function' ? rowKey : (fila) => fila[rowKey]

  return (
    <div className={styles.wrapper}>
      <table className={styles.table} aria-busy={loading || undefined}>
        {caption && <caption className={styles.caption}>{caption}</caption>}
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col" className={styles[col.align ?? 'left']}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Al recargar con filas ya visibles se mantienen (aria-busy avisa); el spinner, solo sin datos. */}
          {loading && rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.estado}>
                <Spinner label="Cargando datos" />
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.estado}>
                <EmptyState message={emptyMessage} />
              </td>
            </tr>
          ) : (
            rows.map((fila) => (
              <tr key={claveDe(fila)} className={rowClassName?.(fila)}>
                {columns.map((col) => (
                  <td key={col.key} className={styles[col.align ?? 'left']}>
                    {col.render ? col.render(fila) : fila[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export function TableFooter({ className, children }) {
  return <div className={cx(styles.footer, className)}>{children}</div>
}
