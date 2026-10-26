import { CheckCheck } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useNotificaciones } from '../../../hooks/useNotificaciones'
import { notificaciones } from '../../../services/notificaciones'
import { cx } from '../../../utils/cx'
import { haceCuanto } from '../../../utils/fechas'
import { Button, Spinner } from '../../ui'
import { NotificationBell } from '../NotificationBell/NotificationBell'
import styles from './NotificationCenter.module.css'

const RECIENTES = 8

/** Campana con desplegable de las últimas notificaciones (RF-073, RF-074). */
export function NotificationCenter({ verTodasPath, inverse = false }) {
  const { noLeidas, actualizar } = useNotificaciones()
  const [abierto, setAbierto] = useState(false)
  const [lista, setLista] = useState(null)
  const contenedor = useRef(null)
  const panelId = useId()

  useEffect(() => {
    if (!abierto) return undefined
    let vigente = true
    notificaciones.listar({ page_size: RECIENTES }).then((datos) => vigente && setLista(datos.results), () => vigente && setLista([]))

    function alClicFuera(evento) {
      if (!contenedor.current?.contains(evento.target)) setAbierto(false)
    }
    function alTeclear(evento) {
      if (evento.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('mousedown', alClicFuera)
    document.addEventListener('keydown', alTeclear)
    return () => {
      vigente = false
      document.removeEventListener('mousedown', alClicFuera)
      document.removeEventListener('keydown', alTeclear)
    }
  }, [abierto])

  async function leer(notificacion) {
    if (notificacion.leida) return
    const leida = await notificaciones.leer(notificacion.id)
    setLista((actual) => actual.map((n) => (n.id === leida.id ? leida : n)))
    actualizar()
  }

  async function leerTodas() {
    await notificaciones.leerTodas()
    setLista((actual) => actual.map((n) => ({ ...n, leida: true })))
    actualizar()
  }

  return (
    <div className={styles.wrapper} ref={contenedor}>
      <NotificationBell
        count={noLeidas}
        inverse={inverse}
        aria-expanded={abierto}
        aria-controls={panelId}
        onClick={() => {
          setLista(null)
          setAbierto((a) => !a)
        }}
      />
      {abierto && (
        <section id={panelId} className={styles.panel} aria-label="Notificaciones recientes">
          <header className={styles.header}>
            <h2 className={styles.titulo}>Notificaciones</h2>
            {noLeidas > 0 && (
              <Button variant="link" size="sm" icon={CheckCheck} onClick={leerTodas}>
                Marcar todas como leídas
              </Button>
            )}
          </header>
          {lista === null ? (
            <div className={styles.estado}>
              <Spinner label="Cargando" />
            </div>
          ) : lista.length === 0 ? (
            <p className={styles.estado}>No tienes notificaciones.</p>
          ) : (
            <ul className={styles.lista}>
              {lista.map((n) => (
                <li key={n.id}>
                  <button type="button" className={cx(styles.item, !n.leida && styles.noLeida)} onClick={() => leer(n)}>
                    <span className={styles.asunto}>
                      {!n.leida && <span className={styles.punto} aria-label="Sin leer" />}
                      {n.asunto}
                    </span>
                    <span className={styles.resumen}>{n.resumen}</span>
                    <time className={styles.fecha} dateTime={n.created_at}>
                      {haceCuanto(n.created_at)}
                    </time>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <footer className={styles.footer}>
            <Link to={verTodasPath} onClick={() => setAbierto(false)}>
              Ver todas
            </Link>
          </footer>
        </section>
      )}
    </div>
  )
}
