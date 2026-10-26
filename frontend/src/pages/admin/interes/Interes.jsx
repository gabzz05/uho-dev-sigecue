import { useState } from 'react'
import { PageHeader, Select, Spinner, Tabs } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useCarga } from '../../../hooks/useCarga'
import { convocatoriasInteres } from '../../../services/interes'
import { Convocatorias } from './Convocatorias'
import styles from './Interes.module.css'
import { Interesados } from './Interesados'
import { Oferta } from './Oferta'

const TABS = [
  { id: 'convocatorias', label: 'Convocatorias' },
  { id: 'oferta', label: 'Oferta de carreras' },
  { id: 'interesados', label: 'Interesados' },
]

const listarConvocatorias = () => convocatoriasInteres.listar({ page_size: 100 }).then((d) => d.results)

/** Oferta o interesados de la convocatoria elegida (por defecto, la más reciente). */
function PorConvocatoria({ tab, elegida, onElegir }) {
  const carga = useCarga(listarConvocatorias)
  if (carga.cargando) return <Spinner label="Cargando convocatorias" />

  const lista = carga.datos ?? []
  const convocatoria = lista.find((c) => String(c.id) === elegida) ?? lista[0] ?? null
  return (
    <div className={styles.pila}>
      {lista.length > 0 && (
        <div className={styles.selector}>
          <Select
            label="Convocatoria"
            options={lista.map((c) => ({ value: String(c.id), label: `${c.anio_academico} (${c.estado_nombre})` }))}
            value={String(convocatoria?.id ?? '')}
            onChange={(e) => onElegir(e.target.value)}
          />
        </div>
      )}
      {tab === 'oferta' ? (
        <Oferta key={convocatoria?.id} convocatoria={convocatoria} />
      ) : (
        <Interesados key={convocatoria?.id} convocatoria={convocatoria} />
      )}
    </div>
  )
}

/** Convocatoria de interés (RF-026 a RF-031): convocatorias, oferta e interesados. */
export function Interes() {
  const { esGlobal, tienePermiso } = useAuth()
  const [tab, setTab] = useState('convocatorias')
  const [elegida, setElegida] = useState('')

  return (
    <>
      <PageHeader title="Interés de la población" subtitle="Convocatorias de interés, oferta de carreras y personas interesadas." />
      <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Sección">
        {tab === 'convocatorias' ? (
          <Convocatorias puedeGestionar={esGlobal && tienePermiso('interes.editar')} />
        ) : (
          // Se monta al entrar en la pestaña: así los estados y totales están al día.
          <PorConvocatoria tab={tab} elegida={elegida} onElegir={setElegida} />
        )}
      </Tabs>
    </>
  )
}
