import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { Alert, Avatar, Badge, Button, Card, CardBody, Spinner, StatusBadge, Stepper } from '../../components/ui'
import { useArchivoPrivado } from '../../hooks/useArchivoPrivado'
import { useAuth } from '../../hooks/useAuth'
import { useCarga } from '../../hooks/useCarga'
import { perfilAspirante, solicitudes } from '../../services/aspirante'
import { publico } from '../../services/publico'
import { formatearFecha } from '../../utils/fechas'
import styles from './Aspirante.module.css'
import { ESTADOS_SOLICITUD, solicitudVigente } from './estados'

const cargar = () => Promise.all([perfilAspirante.obtener(), solicitudes.listar(), publico.convocatoriaSolicitud()])

function diasHasta(fechaIso, hoy = new Date()) {
  const [anio, mes, dia] = fechaIso.split('-').map(Number)
  const inicioHoy = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
  return Math.round((new Date(anio, mes - 1, dia) - inicioHoy) / 86_400_000)
}

/** Pasos del aspirante, del registro a la prematrícula (mockup, panel del aspirante). */
function pasos(perfil, solicitud) {
  const perfilListo = perfil.limites.listo_para_carreras
  const confirmada = solicitud && solicitud.estado !== 'borrador'
  const otorgada = solicitud?.estado === 'otorgada'
  const estado = (hecho, actual) => (hecho ? 'completado' : actual ? 'actual' : 'pendiente')
  return [
    { label: 'Registro', estado: 'completado' },
    { label: 'Verificar correo', estado: 'completado' },
    { label: 'Completar perfil', estado: estado(perfilListo, !perfilListo) },
    { label: 'Seleccionar carreras', estado: estado(confirmada, perfilListo && !confirmada) },
    { label: 'Prematrícula', estado: estado(false, otorgada) },
  ]
}

/** Inicio del portal del aspirante: estado del proceso y siguiente paso. */
export function InicioAspirante() {
  const { usuario } = useAuth()
  const foto = useArchivoPrivado(usuario.foto)
  const carga = useCarga(cargar)

  if (carga.cargando) return <Spinner label="Cargando tu portal" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const [perfil, lista, convocatoria] = carga.datos
  const solicitud = solicitudVigente(lista, Boolean(convocatoria))
  const nombre = `${perfil.nombre} ${perfil.apellidos}`.trim()
  const dias = convocatoria ? diasHasta(convocatoria.fecha_cierre) : null

  return (
    <div className={styles.pila}>
      <Card>
        <CardBody>
          <div className={styles.bienvenida}>
            <Avatar nombre={nombre} foto={foto} size="lg" />
            <div className={styles.bienvenidaTexto}>
              <h1 className={styles.saludo}>Hola, {nombre}</h1>
              <p className={styles.ayuda}>
                CI: {perfil.ci} · {perfil.celular} · {perfil.email}
              </p>
              <div className={styles.insignias}>
                <Badge tone="success">Cuenta verificada</Badge>
                {perfil.perfil_completo ? <Badge tone="success">Perfil completo</Badge> : <Badge tone="warning">Perfil incompleto</Badge>}
              </div>
            </div>
            {convocatoria && (
              <div className={styles.cuentaAtras}>
                <span>Convocatoria activa</span>
                <span>Cierra {dias === 0 ? 'hoy' : dias === 1 ? 'mañana' : `en ${dias} días`}</span>
                <strong>{formatearFecha(convocatoria.fecha_cierre)}</strong>
              </div>
            )}
          </div>
        </CardBody>
      </Card>

      <Stepper steps={pasos(perfil, solicitud)} label="Tu proceso de ingreso" />

      <SiguientePaso perfil={perfil} solicitud={solicitud} hayConvocatoria={Boolean(convocatoria)} />
    </div>
  )
}

function SiguientePaso({ perfil, solicitud, hayConvocatoria }) {
  if (solicitud?.estado === 'otorgada') {
    const plaza = solicitud.carreras.find((c) => c.estado === 'otorgada')?.oferta
    return (
      <Alert tone="success" title="¡Obtuviste plaza!">
        {plaza ? `${plaza.carrera_nombre} en ${plaza.entidad_nombre}. ` : ''}
        Te avisaremos cuando la prematrícula esté disponible.
      </Alert>
    )
  }
  if (solicitud?.estado === 'no_seleccionado' && !hayConvocatoria) {
    return <Alert tone="info">No obtuviste plaza en la última convocatoria. Te avisaremos si se abre una nueva.</Alert>
  }
  if (solicitud?.estado === 'observada') {
    return (
      <Alert
        tone="danger"
        title="Tu solicitud tiene observaciones"
        action={
          <Button as={Link} to="/aspirante/solicitud" size="sm" icon={ArrowRight}>
            Ver observaciones
          </Button>
        }
      >
        Corrige lo observado y envía la corrección. Mientras tanto tu solicitud no participa en el otorgamiento.
      </Alert>
    )
  }
  if (!perfil.limites.listo_para_carreras && !perfil.bloqueado) {
    return (
      <Alert
        tone="warning"
        title="Completa tu perfil"
        action={
          <Button as={Link} to="/aspirante/completar-perfil" size="sm" icon={ArrowRight}>
            Completar perfil
          </Button>
        }
      >
        Sube tu foto, tus documentos e indica tu índice académico y centro de trabajo para poder elegir carreras.
      </Alert>
    )
  }
  if (solicitud) {
    const resumen = solicitud.carreras.map((c) => c.oferta.carrera_nombre).join(', ') || 'sin carreras todavía'
    return (
      <Card>
        <CardBody>
          <div className={styles.resumenSolicitud}>
            <div>
              <strong>Tu solicitud · curso {solicitud.convocatoria.anio_academico}</strong>
              <p className={styles.ayuda}>{resumen}</p>
            </div>
            <StatusBadge estado={solicitud.estado} mapa={ESTADOS_SOLICITUD} />
          </div>
          <Button as={Link} to="/aspirante/solicitud" variant="secondary" icon={ArrowRight}>
            {solicitud.editable ? 'Ver y editar mi solicitud' : 'Ver mi solicitud'}
          </Button>
        </CardBody>
      </Card>
    )
  }
  if (hayConvocatoria) {
    return (
      <Alert
        tone="info"
        title="La convocatoria está abierta"
        action={
          <Button as={Link} to="/aspirante/solicitud" size="sm" icon={ArrowRight}>
            Seleccionar carreras
          </Button>
        }
      >
        Tu perfil está listo. Ya puedes elegir tus carreras.
      </Alert>
    )
  }
  return <Alert tone="info">Tu perfil está listo. Te avisaremos cuando se abra la convocatoria de solicitud de matrícula.</Alert>
}
