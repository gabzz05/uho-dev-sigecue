import { Badge } from '../../../components/ui'
import { CrudPage } from '../../../components/crud/CrudPage'
import { tiposDocumento } from '../../../services/aspirante'

const COLUMNAS = [
  { key: 'orden', header: 'Orden', align: 'center' },
  { key: 'nombre', header: 'Documento', render: (t) => <strong>{t.nombre}</strong> },
  {
    key: 'obligatorio',
    header: 'Requisito',
    render: (t) => (t.obligatorio ? <Badge tone="info">Obligatorio</Badge> : <Badge>Opcional</Badge>),
  },
]

const CAMPOS = [
  { name: 'nombre', label: 'Nombre', required: true },
  { name: 'orden', label: 'Orden', type: 'number', ancho: 'mitad', hint: 'Posición en el perfil del aspirante.' },
  { name: 'obligatorio', label: 'Obligatorio para completar el perfil', type: 'checkbox' },
]

/** Documentos que se piden al aspirante en su perfil (RF-046). PDF, JPG o PNG de hasta 5 MB. */
export function TiposDocumento({ editable }) {
  return (
    <CrudPage
      conEncabezado={false}
      singular="documento"
      recurso={tiposDocumento}
      columnas={COLUMNAS}
      campos={CAMPOS}
      valoresIniciales={{ nombre: '', orden: 0, obligatorio: true }}
      validar={(v) => (v.nombre.trim() ? {} : { nombre: 'Indica el nombre del documento.' })}
      aDatos={(v) => ({ nombre: v.nombre.trim(), orden: Number(v.orden) || 0, obligatorio: Boolean(v.obligatorio) })}
      placeholderBusqueda="Nombre"
      permisos={{ crear: editable, editar: editable, eliminar: editable }}
    />
  )
}
