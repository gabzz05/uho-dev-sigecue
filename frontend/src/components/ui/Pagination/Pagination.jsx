import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '../Button/Button'
import styles from './Pagination.module.css'

/** Paginación compatible con la respuesta de la API (`count` + `page_size`). */
export function Pagination({ page, count, pageSize, onChange }) {
  const totalPaginas = Math.max(1, Math.ceil(count / pageSize))
  const desde = count === 0 ? 0 : (page - 1) * pageSize + 1
  const hasta = Math.min(page * pageSize, count)

  return (
    <nav className={styles.pagination} aria-label="Paginación">
      <span className={styles.info}>
        Mostrando {desde}–{hasta} de {count}
      </span>
      <div className={styles.controls}>
        <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Anterior
        </Button>
        <span className={styles.page} aria-current="page">
          Página {page} de {totalPaginas}
        </span>
        <Button
          variant="secondary"
          size="sm"
          icon={ChevronRight}
          disabled={page >= totalPaginas}
          onClick={() => onChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  )
}
