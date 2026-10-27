import { CheckCircle2, FileSpreadsheet, FileText, Minus, Send, Shuffle, Undo2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Termometro } from '../../../components/graficos/Graficos'
import {
  Alert,
  Badge,
  BotonConfirmado,
  Button,
  Card,
  CardBody,
  CardHeader,
  Checkbox,
  DataTable,
  Input,
  KpiCard,
  Modal,
  Pagination,
  Select,
  Stepper,
  TableFooter,
  Tabs,
  Textarea,
  Toolbar,
  useToast,
} from '../../../components/ui'
import { useListado } from '../../../hooks/useListado'
import { mensajeDeError } from '../../../services/errores'
import { otorgamientos } from '../../../services/otorgamiento'
import { descargarBlob } from '../../../utils/descargar'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Otorgamiento.module.css'

const ORDEN_ETAPAS = ['revision_ci', 'aprobacion', 'publicado']

function pasos(estado) {
  const actual = ORDEN_ETAPAS.indexOf(estado)
  const etapa = (i) => (estado === 'publicado' || i < actual ? 'completado' : i === actual ? 'actual' : 'pendiente')
  return [
    { label: 'Generado', estado: 'completado' },
    { label: 'Revisión del Jefe CI', estado: etapa(0) },
    { label: 'Aprobación del Vicerrector', estado: etapa(1) },
    { label: 'Publicado', estado: estado === 'publicado' ? 'completado' : 'pendiente' },
  ]
}

const TABS = [
  { id: 'resultados', label: 'Resultados' },
  { id: 'plazas', label: 'Plazas por oferta' },
  { id: 'ajustes', label: 'Ajustes manuales' },
]

/** Un otorgamiento: etapas, resultado, ajustes, aprobación y publicación. */
export function DetalleOtorgamiento({ inicial }) {
  const toast = useToast()
  const [otorgamiento, setOtorgamiento] = useState(inicial)
  const [tab, setTab] = useState('resultados')
  const [version, setVersion] = useState(0)
  const [publicando, setPublicando] = useState(false)
  const [exportando, setExportando] = useState(null)
  const { permisos, totales, convocatoria } = otorgamiento

  const refrescar = useCallback(async () => {
    setOtorgamiento(await otorgamientos.obtener(otorgamiento.id))
    setVersion((v) => v + 1)
  }, [otorgamiento.id])

  async function aprobar() {
    try {
      setOtorgamiento(await otorgamientos.aprobar(otorgamiento.id))
      toast.exito('Aprobado. Pasa a la aprobación del Vicerrector.')
    } catch (e) {
      toast.error(mensajeDeError(e))
    }
  }

  async function exportar(formato) {
    setExportando(formato)
    try {
      const archivo = formato === 'pdf' ? await otorgamientos.exportarPdf(otorgamiento.id) : await otorgamientos.exportarExcel(otorgamiento.id)
      descargarBlob(archivo, `otorgamiento-${convocatoria.anio_academico}-${convocatoria.numero}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`)
    } catch (e) {
      toast.error(mensajeDeError(e))
    } finally {
      setExportando(null)
    }
  }

  const ayuda = {
    revision_ci: 'El Jefe de la Comisión de Ingreso revisa el reparto, lo ajusta si hace falta (con justificación) y lo aprueba.',
    aprobacion: 'El Vicerrector de Formación revisa y puede ajustar. Al aprobarlo se publica y se avisa a los aspirantes.',
    publicado: `Publicado el ${formatearFechaHora(otorgamiento.publicado_at)} por ${otorgamiento.publicado_por ?? '—'}. Ya no admite cambios.`,
  }[otorgamiento.estado]

  return (
    <div className={styles.pila}>
      <Stepper steps={pasos(otorgamiento.estado)} label="Etapas del otorgamiento" />
      <Alert tone={otorgamiento.estado === 'publicado' ? 'success' : 'info'} title={otorgamiento.estado_nombre}>
        {ayuda}
        {otorgamiento.estado !== 'publicado' && ' Hasta la publicación, el resultado es provisional y los aspirantes no lo ven.'}
      </Alert>

      <div className={styles.kpis}>
        <KpiCard label="Plazas otorgadas" value={totales.otorgadas} hint={`de ${totales.plazas} disponibles`} />
        <KpiCard label="Elegibles" value={totales.elegibles} tone="success" />
        <KpiCard label="No elegibles" value={totales.resultados - totales.elegibles} tone="warning" />
      </div>

      <div className={styles.acciones}>
        {permisos.exportar && (
          <>
            <Button variant="secondary" icon={FileSpreadsheet} loading={exportando === 'excel'} onClick={() => exportar('excel')}>
              Excel
            </Button>
            <Button variant="secondary" icon={FileText} loading={exportando === 'pdf'} onClick={() => exportar('pdf')}>
              PDF
            </Button>
          </>
        )}
        {permisos.aprobar && (
          <BotonConfirmado
            icon={CheckCircle2}
            titulo="Aprobar otorgamiento"
            mensaje="Pasará a la aprobación del Vicerrector y ya no podrás ajustarlo."
            onConfirm={aprobar}
          >
            Aprobar
          </BotonConfirmado>
        )}
        {permisos.publicar && (
          <Button icon={Send} onClick={() => setPublicando(true)}>
            Aprobar y publicar
          </Button>
        )}
      </div>

      <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Detalle del otorgamiento">
        {tab === 'resultados' && <Resultados otorgamiento={otorgamiento} version={version} onAjustado={refrescar} />}
        {tab === 'plazas' && (
          <Card>
            <CardBody>
              <Termometro
                unidad="otorgadas"
                referenciaNombre="plazas"
                filas={otorgamiento.plazas.map((p) => ({ clave: p.oferta, etiqueta: p.carrera, detalle: p.entidad, valor: p.otorgadas, referencia: p.plazas }))}
              />
            </CardBody>
          </Card>
        )}
        {tab === 'ajustes' && <Ajustes otorgamiento={otorgamiento} version={version} onAnulado={refrescar} />}
      </Tabs>

      {publicando && (
        <Publicar
          otorgamiento={otorgamiento}
          onClose={() => setPublicando(false)}
          onPublicado={(o) => {
            setOtorgamiento(o)
            setVersion((v) => v + 1)
          }}
        />
      )}
    </div>
  )
}

function Resultados({ otorgamiento, version, onAjustado }) {
  const recurso = useMemo(() => otorgamientos.resultados(otorgamiento.id), [otorgamiento.id])
  const listado = useListado(recurso, { filtrosIniciales: { buscar: '', otorgados: '', elegibles: '' }, pageSize: 50 })
  const [ajustando, setAjustando] = useState(null)
  const { recargar } = listado
  const editar = otorgamiento.permisos.editar

  useEffect(() => {
    if (version > 0) recargar()
  }, [version, recargar])

  const filtro = (nombre) => ({ value: listado.filtros[nombre], onChange: (e) => listado.cambiarFiltro(nombre, e.target.value) })

  const columnas = [
    { key: 'posicion_ranking', header: 'Pos.', align: 'center', render: (r) => r.posicion_ranking ?? '—' },
    { key: 'aspirante_nombre', header: 'Aspirante', render: (r) => <strong>{r.aspirante_nombre}</strong> },
    { key: 'indice_utilizado', header: 'Índice', align: 'center', render: (r) => r.indice_utilizado ?? '—' },
    {
      key: 'resultado',
      header: 'Resultado',
      render: (r) =>
        r.motivo_exclusion ? (
          <span className={styles.apagado}>No elegible: {r.motivo_exclusion}</span>
        ) : r.otorgada ? (
          <span>
            {r.carrera} <span className={styles.apagado}>— {r.entidad} · {r.prioridad}.ª opción</span>
            {r.tipo === 'manual' && <Badge tone="accent">Manual</Badge>}
          </span>
        ) : (
          <span className={styles.apagado}>Sin plaza</span>
        ),
    },
    ...(editar
      ? [
          {
            key: 'acciones',
            header: 'Acciones',
            render: (r) =>
              !r.motivo_exclusion && (
                <Button variant="ghost" size="sm" icon={Shuffle} onClick={() => setAjustando(r)} aria-label={`Ajustar a ${r.aspirante_nombre}`}>
                  Ajustar
                </Button>
              ),
          },
        ]
      : []),
  ]

  return (
    <Card>
      <Toolbar>
        <Input label="Buscar" type="search" placeholder="Nombre" {...filtro('buscar')} />
        <Select
          label="Resultado"
          placeholder="Todos"
          options={[
            { value: 'true', label: 'Con plaza' },
            { value: 'false', label: 'Sin plaza' },
          ]}
          {...filtro('otorgados')}
        />
        <Select
          label="Elegibilidad"
          placeholder="Todas"
          options={[
            { value: 'true', label: 'Elegibles' },
            { value: 'false', label: 'No elegibles' },
          ]}
          {...filtro('elegibles')}
        />
      </Toolbar>
      {listado.error && <Alert tone="danger">{listado.error}</Alert>}
      <DataTable columns={columnas} rows={listado.filas} loading={listado.cargando} emptyMessage="No hay resultados con esos filtros." />
      <TableFooter>
        <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
      </TableFooter>
      {ajustando && (
        <Ajustar
          otorgamiento={otorgamiento}
          resultado={ajustando}
          onClose={() => setAjustando(null)}
          onAjustado={onAjustado}
        />
      )}
    </Card>
  )
}

function Ajustar({ otorgamiento, resultado, onClose, onAjustado }) {
  const toast = useToast()
  const [opcion, setOpcion] = useState('')
  const [justificacion, setJustificacion] = useState('')
  const [error, setError] = useState('')
  const [cambios, setCambios] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const quitadas = new Set(resultado.opciones_quitadas)

  async function enviar(tipo, opcionId) {
    setOpcion(opcionId)
    if (!justificacion.trim()) {
      setError('La justificación es obligatoria.')
      return
    }
    setOcupado(true)
    setError('')
    try {
      const respuesta = await otorgamientos.ajustar(otorgamiento.id, { resultado: resultado.id, tipo, opcion: opcionId, justificacion: justificacion.trim() })
      setCambios(respuesta.cambios)
      toast.exito('Se aplicó el ajuste.')
      onAjustado()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Ajustar a ${resultado.aspirante_nombre}`}
      description="Solo entre las carreras que solicitó. El reparto se recalcula y cubre en cascada las vacantes; nunca se supera el plan."
      size="lg"
      footer={
        <Button variant="secondary" onClick={onClose}>
          {cambios ? 'Cerrar' : 'Cancelar'}
        </Button>
      }
    >
      {cambios ? (
        <div className={styles.formulario}>
          <strong>Cambios en el reparto</strong>
          {cambios.length === 0 ? (
            <p className={styles.apagado}>El reparto no cambió.</p>
          ) : (
            <ul className={styles.motivos}>
              {cambios.map((c) => (
                <li key={c.resultado}>
                  {c.aspirante}: {c.antes ?? 'sin plaza'} → <strong>{c.despues ?? 'sin plaza'}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className={styles.formulario}>
          {error && <Alert tone="danger">{error}</Alert>}
          <Textarea label="Justificación" required rows={3} maxLength={2000} value={justificacion} onChange={(e) => setJustificacion(e.target.value)} />
          <ul className={styles.opciones}>
            {resultado.opciones.map((o) => {
              const actual = resultado.otorgada === o.opcion
              return (
                <li key={o.opcion}>
                  <span>
                    {o.prioridad}. {o.carrera} <span className={styles.apagado}>— {o.entidad}</span>
                    {actual && <Badge tone="success">Otorgada</Badge>}
                    {quitadas.has(o.opcion) && <Badge tone="warning">Quitada</Badge>}
                  </span>
                  {actual ? (
                    <Button variant="ghost" size="sm" icon={Minus} loading={ocupado && opcion === o.opcion} onClick={() => enviar('quitar', o.opcion)}>
                      Quitar
                    </Button>
                  ) : (
                    <Button variant="secondary" size="sm" loading={ocupado && opcion === o.opcion} onClick={() => enviar('otorgar', o.opcion)}>
                      Otorgar esta
                    </Button>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </Modal>
  )
}

function Ajustes({ otorgamiento, version, onAnulado }) {
  const toast = useToast()
  const [ajustes, setAjustes] = useState(null)
  const [anulando, setAnulando] = useState(null)
  const [motivo, setMotivo] = useState('')

  useEffect(() => {
    let vigente = true
    otorgamientos.ajustes(otorgamiento.id).then((a) => vigente && setAjustes(a), () => vigente && setAjustes([]))
    return () => {
      vigente = false
    }
  }, [otorgamiento.id, version])

  async function anular() {
    try {
      await otorgamientos.anularAjuste(otorgamiento.id, anulando.id, motivo.trim())
      toast.exito('Se anuló el ajuste y se recalculó el reparto.')
      setAnulando(null)
      setMotivo('')
      onAnulado()
    } catch (e) {
      toast.error(mensajeDeError(e))
    }
  }

  if (ajustes === null) return null
  return (
    <Card>
      <CardHeader title="Ajustes manuales" />
      <CardBody>
        {ajustes.length === 0 ? (
          <p className={styles.apagado}>Sin ajustes: el reparto es el automático.</p>
        ) : (
          <ul className={styles.ajustes}>
            {ajustes.map((a) => (
              <li key={a.id}>
                <div>
                  <strong>
                    {a.tipo_nombre} {a.opcion_texto} a {a.aspirante}
                  </strong>
                  {!a.activo && <Badge>Anulado</Badge>}
                </div>
                <span className={styles.apagado}>
                  {a.usuario} · {formatearFechaHora(a.created_at)} · {a.justificacion}
                </span>
                {!a.activo && (
                  <span className={styles.apagado}>
                    Anulado por {a.anulado_por} el {formatearFechaHora(a.anulado_at)}: {a.justificacion_anulacion}
                  </span>
                )}
                {a.activo && otorgamiento.permisos.editar && (
                  <Button variant="ghost" size="sm" icon={Undo2} onClick={() => setAnulando(a)}>
                    Anular
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
      <Modal
        open={Boolean(anulando)}
        onClose={() => setAnulando(null)}
        title="Anular ajuste"
        footer={
          <>
            <Button variant="secondary" onClick={() => setAnulando(null)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={anular} disabled={!motivo.trim()}>
              Anular
            </Button>
          </>
        }
      >
        <Textarea label="Motivo" required rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
      </Modal>
    </Card>
  )
}

function Publicar({ otorgamiento, onClose, onPublicado }) {
  const toast = useToast()
  const [segunda, setSegunda] = useState(false)
  const [ocupado, setOcupado] = useState(false)

  async function publicar() {
    setOcupado(true)
    try {
      onPublicado(await otorgamientos.publicar(otorgamiento.id, segunda))
      toast.exito('Se publicó el otorgamiento y se avisó a los aspirantes.')
      onClose()
    } catch (e) {
      toast.error(mensajeDeError(e))
      setOcupado(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Aprobar y publicar"
      description="El resultado queda congelado, cambia el estado de las solicitudes y se avisa a todos los aspirantes. No se puede deshacer."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={ocupado}>
            Cancelar
          </Button>
          <Button onClick={publicar} loading={ocupado}>
            Aprobar y publicar
          </Button>
        </>
      }
    >
      <Checkbox
        label="Habrá segunda convocatoria (los no seleccionados reciben un aviso para participar en ella)"
        checked={segunda}
        onChange={(e) => setSegunda(e.target.checked)}
      />
    </Modal>
  )
}
