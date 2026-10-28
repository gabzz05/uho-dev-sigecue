import { AlertTriangle, ArrowRight, Info, OctagonAlert } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { MENU_ADMIN } from '../../components/layout'
import { Alert, Button, Card, CardBody, CardHeader, PageHeader, Spinner } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { usePolling } from '../../hooks/usePolling'
import { obtenerDashboard } from '../../services/dashboard'
import { mensajeDeError } from '../../services/errores'
import { cx } from '../../utils/cx'
import { ESTADOS_PREMATRICULA } from '../../utils/estadosPrematricula'
import { ESTADOS_SOLICITUD } from '../../utils/estadosSolicitud'
import { formatearFecha, formatearFechaHora } from '../../utils/fechas'
import styles from './Dashboard.module.css'

const ICONO_ALERTA = { atencion: OctagonAlert, aviso: AlertTriangle, info: Info }

/** Una tarjeta por módulo: qué está pasando y a dónde ir. */
const SECCIONES = {
  interes: {
    titulo: 'Convocatoria de interés',
    enlace: '/admin/interes',
    filas: (s) => [
      ['Curso', `${s.anio_academico} · ${s.estado}`],
      ['Expresiones de interés', s.expresiones],
      ['Cierre', formatearFecha(s.fecha_cierre)],
    ],
  },
  plan_plazas: {
    titulo: 'Plan de plazas',
    enlace: (s) => `/admin/plan-plazas/${s.id}`,
    filas: (s) => [
      ['Curso', s.anio_academico],
      ['Estado', s.estado],
      ...(s.entidades_pendientes ? [['Entidades sin responder', s.entidades_pendientes]] : []),
    ],
  },
  solicitudes: {
    titulo: 'Solicitudes',
    enlace: '/admin/solicitudes',
    filas: (s) => [
      ['Convocatoria', `${s.convocatoria} · ${s.estado_convocatoria}`],
      ['Confirmadas', s.total],
      ...Object.entries(s.por_estado)
        .filter(([, n]) => n > 0)
        .map(([estado, n]) => [ESTADOS_SOLICITUD[estado]?.label ?? estado, n]),
    ],
  },
  otorgamiento: {
    titulo: 'Otorgamiento',
    enlace: '/admin/otorgamiento',
    filas: (s) => [
      ['Convocatoria', s.convocatoria],
      ['Estado', s.estado],
      ...(s.otorgadas != null ? [['Plazas otorgadas', s.otorgadas]] : []),
    ],
  },
  prematricula: {
    titulo: 'Prematrícula',
    enlace: '/admin/prematricula',
    filas: (s) => [
      ['Expedientes', s.total],
      ['Cierre', formatearFecha(s.fecha_cierre)],
      ...Object.entries(s.por_estado)
        .filter(([, n]) => n > 0)
        .map(([estado, n]) => [ESTADOS_PREMATRICULA[estado]?.label ?? estado, n]),
    ],
  },
}

/** Dashboard principal: vista ejecutiva por rol, alertas operativas y accesos rápidos (RF-030). Se actualiza cada 60 s. */
export function Dashboard() {
  const { usuario, tienePermiso } = useAuth()
  const [estado, setEstado] = useState({ datos: null, error: '' })
  const actualizar = useCallback(() => {
    obtenerDashboard()
      .then((datos) => setEstado({ datos, error: '' }))
      .catch((error) => setEstado((e) => ({ ...e, error: mensajeDeError(error) })))
  }, [])
  usePolling(actualizar)

  const accesos = MENU_ADMIN.flatMap((s) => s.items).filter((i) => i.path && tienePermiso(i.permiso))
  const { datos } = estado

  return (
    <>
      <PageHeader title="Dashboard" subtitle={`Bienvenido(a), ${usuario.nombre || usuario.username}`} />
      {!datos ? (
        estado.error ? <Alert tone="danger">{estado.error}</Alert> : <Spinner label="Cargando el dashboard" />
      ) : (
        <div className={styles.pila}>
          {datos.alertas.length > 0 && (
            <section aria-labelledby="titulo-alertas">
              <h2 id="titulo-alertas" className={styles.subtitulo}>
                Requiere atención
              </h2>
              <ul className={styles.alertas}>
                {datos.alertas.map((a) => {
                  const Icono = ICONO_ALERTA[a.nivel]
                  return (
                    <li key={a.texto} className={cx(styles.alerta, styles[a.nivel])}>
                      <Icono aria-hidden="true" className={styles.iconoAlerta} />
                      <span>{a.texto}</span>
                      <Link to={a.enlace} className={styles.enlaceAlerta}>
                        Ir <ArrowRight aria-hidden="true" />
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </section>
          )}

          {Object.keys(datos.secciones).length === 0 ? (
            <Alert tone="info">Todavía no hay procesos en marcha que mostrar.</Alert>
          ) : (
            <div className={styles.secciones}>
              {Object.entries(datos.secciones).map(([modulo, seccion]) => {
                const definicion = SECCIONES[modulo]
                const enlace = typeof definicion.enlace === 'function' ? definicion.enlace(seccion) : definicion.enlace
                return (
                  <Card key={modulo}>
                    <CardHeader
                      title={definicion.titulo}
                      actions={
                        <Button as={Link} to={enlace} variant="ghost" size="sm" icon={ArrowRight} aria-label={`Abrir ${definicion.titulo}`}>
                          Abrir
                        </Button>
                      }
                    />
                    <CardBody>
                      <dl className={styles.datos}>
                        {definicion.filas(seccion).map(([etiqueta, valor]) => (
                          <div key={etiqueta} className={styles.dato}>
                            <dt>{etiqueta}</dt>
                            <dd>{valor}</dd>
                          </div>
                        ))}
                      </dl>
                    </CardBody>
                  </Card>
                )
              })}
            </div>
          )}

          <section aria-labelledby="titulo-accesos">
            <h2 id="titulo-accesos" className={styles.subtitulo}>
              Accesos rápidos
            </h2>
            <nav className={styles.accesos} aria-labelledby="titulo-accesos">
              {accesos.map(({ path, label, icon: Icono }) => (
                <Link key={path} to={`/admin/${path}`} className={styles.acceso}>
                  {Icono && <Icono aria-hidden="true" />}
                  {label}
                </Link>
              ))}
            </nav>
          </section>
          <p className={styles.apagado}>Actualizado {formatearFechaHora(datos.actualizado)}</p>
        </div>
      )}
    </>
  )
}
