import { Plus } from 'lucide-react'
import { useState } from 'react'
import { Alert, Badge, Button, Card, DataTable, PageHeader, Pagination, TableFooter, useToast } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useListado } from '../../../hooks/useListado'
import { envios } from '../../../services/notificaciones'
import { formatearFechaHora } from '../../../utils/fechas'
import { NuevoEnvio } from './NuevoEnvio'

const COLUMNAS = [
  { key: 'created_at', header: 'Fecha', render: (e) => formatearFechaHora(e.created_at) },
  { key: 'asunto', header: 'Asunto', render: (e) => <strong>{e.asunto}</strong> },
  { key: 'grupo_descripcion', header: 'Destinatarios' },
  { key: 'destinatarios', header: 'Nº', align: 'center' },
  {
    key: 'por_correo',
    header: 'Canal',
    render: (e) => <Badge tone={e.por_correo ? 'info' : 'neutral'}>{e.por_correo ? 'In-app + correo' : 'In-app'}</Badge>,
  },
  { key: 'enviado_por_nombre', header: 'Enviado por' },
]

/** Historial y creación de notificaciones masivas (RF-076). */
export function EnviosMasivos() {
  const { tienePermiso } = useAuth()
  const listado = useListado(envios)
  const toast = useToast()
  const [nuevo, setNuevo] = useState(false)

  function cerrar(envio) {
    setNuevo(false)
    if (envio) {
      toast.exito(`Notificación enviada a ${envio.destinatarios} destinatario(s).`)
      listado.recargar()
    }
  }

  return (
    <>
      <PageHeader
        title="Envíos masivos"
        subtitle="Notificaciones a grupos de usuarios. Los roles locales solo envían dentro de su entidad."
        actions={
          tienePermiso('notificaciones.crear') && (
            <Button icon={Plus} onClick={() => setNuevo(true)}>
              Nuevo envío
            </Button>
          )
        }
      />
      <Card>
        {listado.error && <Alert tone="danger">{listado.error}</Alert>}
        <DataTable columns={COLUMNAS} rows={listado.filas} loading={listado.cargando} emptyMessage="Todavía no hay envíos." />
        <TableFooter>
          <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
        </TableFooter>
      </Card>
      {nuevo && <NuevoEnvio onClose={cerrar} />}
    </>
  )
}
