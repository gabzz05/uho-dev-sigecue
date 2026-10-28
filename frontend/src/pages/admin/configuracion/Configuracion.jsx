import { useState } from 'react'
import { Alert, PageHeader, Tabs } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { CamposPrematricula } from './CamposPrematricula'
import { Correo } from './Correo'
import { Identidad } from './Identidad'
import { Parametros } from './Parametros'
import styles from './Configuracion.module.css'
import { Plantillas } from './Plantillas'
import { TiposDocumento } from './TiposDocumento'

const TABS = [
  { id: 'parametros', label: 'Parámetros' },
  { id: 'correo', label: 'Correo' },
  { id: 'plantillas', label: 'Plantillas de correo' },
  { id: 'identidad', label: 'Identidad visual' },
  { id: 'documentos', label: 'Documentos del aspirante' },
  { id: 'prematricula', label: 'Campos de prematrícula' },
]
const PANELES = { parametros: Parametros, correo: Correo, plantillas: Plantillas, identidad: Identidad, documentos: TiposDocumento, prematricula: CamposPrematricula }

/** Configuración del sistema (sección 5.1). Solo el Superadmin la modifica. */
export function Configuracion() {
  const { usuario } = useAuth()
  const [tab, setTab] = useState('parametros')
  const editable = Boolean(usuario.es_superadmin)
  const Panel = PANELES[tab]

  return (
    <>
      <PageHeader title="Configuración" subtitle="Parámetros, correo, plantillas, identidad visual y documentos que se piden al aspirante." />
      <div className={styles.pila}>
        {!editable && (
          <Alert tone="info">Solo el Superadmin puede modificar la configuración. Estás viéndola en modo lectura.</Alert>
        )}
        <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Sección de la configuración">
          <Panel editable={editable} />
        </Tabs>
      </div>
    </>
  )
}
