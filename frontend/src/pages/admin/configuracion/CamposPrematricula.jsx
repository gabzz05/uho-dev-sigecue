import { CrudPage } from '../../../components/crud/CrudPage'
import { Badge } from '../../../components/ui'
import { camposPrematricula } from '../../../services/prematricula'

const TIPOS = [
  { value: 'archivo', label: 'Archivo (PDF, JPG o PNG)' },
  { value: 'imagen', label: 'Imagen (JPG o PNG)' },
  { value: 'texto', label: 'Texto' },
]
const NOMBRE_TIPO = Object.fromEntries(TIPOS.map((t) => [t.value, t.label]))

const COLUMNAS = [
  { key: 'orden', header: 'Orden', align: 'center' },
  { key: 'nombre', header: 'Campo', render: (c) => <strong>{c.nombre}</strong> },
  { key: 'tipo', header: 'Tipo', render: (c) => NOMBRE_TIPO[c.tipo] },
  { key: 'requerido', header: 'Requisito', render: (c) => (c.requerido ? <Badge tone="info">Requerido</Badge> : <Badge>Opcional</Badge>) },
]

const CAMPOS = [
  { name: 'nombre', label: 'Nombre', required: true },
  { name: 'tipo', label: 'Tipo', type: 'select', options: TIPOS, required: true, ancho: 'mitad' },
  { name: 'orden', label: 'Orden', type: 'number', ancho: 'mitad' },
  { name: 'requerido', label: 'Requerido para enviar la prematrícula', type: 'checkbox' },
]

/**
 * Campos y documentos del formulario de prematrícula (RF-010, RF-066).
 * CI y certificación no van aquí: se reutilizan del perfil del aspirante.
 */
export function CamposPrematricula({ editable }) {
  return (
    <CrudPage
      conEncabezado={false}
      singular="campo"
      recurso={camposPrematricula}
      columnas={COLUMNAS}
      campos={CAMPOS}
      valoresIniciales={{ nombre: '', tipo: 'archivo', orden: 0, requerido: true }}
      validar={(v) => (v.nombre.trim() ? {} : { nombre: 'Indica el nombre del campo.' })}
      aDatos={(v) => ({ nombre: v.nombre.trim(), tipo: v.tipo, orden: Number(v.orden) || 0, requerido: Boolean(v.requerido) })}
      placeholderBusqueda="Nombre"
      permisos={{ crear: editable, editar: editable, eliminar: editable }}
    />
  )
}
