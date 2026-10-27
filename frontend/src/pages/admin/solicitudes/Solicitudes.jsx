import { useState } from 'react'
import { PageHeader, Select, Tabs } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { convocatoriasSolicitud } from '../../../services/convocatorias'
import { Estadisticas } from './Estadisticas'
import { ListadoSolicitudes } from './ListadoSolicitudes'
import styles from './Solicitudes.module.css'

const TABS = [
  { id: 'listado', label: 'Solicitudes' },
  { id: 'estadisticas', label: 'Estadísticas' },
]

const etiquetaConvocatoria = (c) => `${c.numero}.ª convocatoria ${c.anio_academico}`

/** Gestión de solicitudes (RF-052 a RF-056). Cada entidad ve las solicitudes con opciones suyas. */
export function Solicitudes() {
  const { tienePermiso } = useAuth()
  const [tab, setTab] = useState('listado')
  const [convocatoria, setConvocatoria] = useState('')
  // Elegir convocatoria exige poder listarlas; sin ese permiso se ven todas y las estadísticas usan la más reciente.
  const opciones = useOpciones(tienePermiso('convocatorias.ver') ? convocatoriasSolicitud : null, { etiqueta: etiquetaConvocatoria })

  return (
    <>
      <PageHeader title="Solicitudes" subtitle="Solicitudes de matrícula recibidas: revisión, observaciones y estadísticas." />
      {opciones.length > 0 && (
        <div className={styles.selectorConvocatoria}>
          <Select
            label="Convocatoria"
            placeholder={tab === 'listado' ? 'Todas' : 'La más reciente'}
            options={opciones}
            value={convocatoria}
            onChange={(e) => setConvocatoria(e.target.value)}
          />
        </div>
      )}
      <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Vista de solicitudes">
        {tab === 'listado' ? <ListadoSolicitudes convocatoria={convocatoria} /> : <Estadisticas convocatoria={convocatoria} />}
      </Tabs>
    </>
  )
}
