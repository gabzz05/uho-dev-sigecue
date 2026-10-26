import { CheckCheck, ChevronDown, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Alert, Button, Card, EmptyState, PageHeader, Pagination, Select, Spinner, TableFooter, Toolbar, useToast } from '../../components/ui'
import { useListado } from '../../hooks/useListado'
import { useNotificaciones } from '../../hooks/useNotificaciones'
import { mensajeDeError } from '../../services/errores'
import { notificaciones } from '../../services/notificaciones'
import { cx } from '../../utils/cx'
import { formatearFechaHora, haceCuanto } from '../../utils/fechas'
import styles from './MisNotificaciones.module.css'

const ESTADOS = [
  { value: 'false', label: 'Sin leer' },
  { value: 'true', label: 'Leídas' },
]

/** Todas las notificaciones del usuario (RF-074). Común a internos y aspirantes. */
export function MisNotificaciones() {
  const listado = useListado(notificaciones, { filtrosIniciales: { leida: '' } })
  const { noLeidas, actualizar } = useNotificaciones()
  const toast = useToast()
  const [abierta, setAbierta] = useState(null)

  async function ejecutar(accion, mensaje) {
    try {
      await accion()
      if (mensaje) toast.exito(mensaje)
      listado.recargar()
      actualizar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  function alternar(notificacion) {
    setAbierta((actual) => (actual === notificacion.id ? null : notificacion.id))
    if (!notificacion.leida) ejecutar(() => notificaciones.leer(notificacion.id))
  }

  return (
    <>
      <PageHeader
        title="Mis notificaciones"
        actions={
          noLeidas > 0 && (
            <Button variant="secondary" icon={CheckCheck} onClick={() => ejecutar(notificaciones.leerTodas, 'Todas marcadas como leídas.')}>
              Marcar todas como leídas
            </Button>
          )
        }
      />
      <Card>
        <Toolbar>
          <Select
            label="Mostrar"
            placeholder="Todas"
            options={ESTADOS}
            value={listado.filtros.leida}
            onChange={(e) => listado.cambiarFiltro('leida', e.target.value)}
          />
        </Toolbar>
        {listado.error && <Alert tone="danger">{listado.error}</Alert>}
        {/* El spinner solo en la primera carga: al recargar se mantiene la lista (y lo desplegado). */}
        {listado.cargando && listado.filas.length === 0 ? (
          <div className={styles.estado}>
            <Spinner label="Cargando notificaciones" />
          </div>
        ) : listado.filas.length === 0 ? (
          <EmptyState title="No hay notificaciones" message="Aquí verás los avisos del proceso de ingreso." />
        ) : (
          <ul className={styles.lista}>
            {listado.filas.map((n) => {
              const expandida = abierta === n.id
              return (
                <li key={n.id} className={cx(styles.item, !n.leida && styles.noLeida)}>
                  <button
                    type="button"
                    className={styles.cabecera}
                    aria-expanded={expandida}
                    aria-controls={`notificacion-${n.id}`}
                    onClick={() => alternar(n)}
                  >
                    <span className={styles.textos}>
                      <span className={styles.asunto}>
                        {!n.leida && <span className={styles.punto} aria-label="Sin leer" />}
                        {n.asunto}
                      </span>
                      {!expandida && <span className={styles.resumen}>{n.resumen}</span>}
                    </span>
                    <time className={styles.fecha} dateTime={n.created_at} title={formatearFechaHora(n.created_at)}>
                      {haceCuanto(n.created_at)}
                    </time>
                    <ChevronDown className={cx(styles.chevron, expandida && styles.girado)} aria-hidden="true" />
                  </button>
                  {expandida && (
                    <div id={`notificacion-${n.id}`} className={styles.cuerpo}>
                      <p>{n.cuerpo}</p>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Trash2}
                        onClick={() => ejecutar(() => notificaciones.eliminar(n.id), 'Notificación eliminada.')}
                      >
                        Eliminar
                      </Button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
        <TableFooter>
          <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
        </TableFooter>
      </Card>
    </>
  )
}
