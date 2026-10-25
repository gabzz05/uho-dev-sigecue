import { useEffect, useState } from 'react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { Alert, Badge } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { roles } from '../../../services/usuarios'
import { MatrizPermisos } from './MatrizPermisos'

const AMBITOS = [
  { value: 'global', label: 'Global' },
  { value: 'facultad', label: 'Local — Facultad' },
  { value: 'cum_fum', label: 'Local — CUM/FUM' },
]
const NOMBRE_AMBITO = Object.fromEntries([...AMBITOS, { value: 'propio', label: 'Propio (aspirante)' }].map((a) => [a.value, a.label]))

const INICIALES = { nombre: '', codigo: '', ambito: '', requiere_area: false, descripcion: '', permisos: [] }

const COLUMNAS = [
  {
    key: 'nombre',
    header: 'Rol',
    render: (r) => (
      <>
        <strong>{r.nombre}</strong> {r.es_sistema && <Badge tone="info">Sistema</Badge>}
      </>
    ),
  },
  { key: 'codigo', header: 'Código' },
  { key: 'ambito', header: 'Ámbito', render: (r) => NOMBRE_AMBITO[r.ambito] ?? r.ambito },
  {
    key: 'permisos',
    header: 'Permisos',
    align: 'center',
    render: (r) => (r.codigo === 'superadmin' ? 'Todos' : r.permisos.length),
  },
]

function validar(v) {
  const errores = {}
  if (!v.nombre.trim()) errores.nombre = 'Escribe el nombre del rol.'
  if (!/^[a-z0-9_-]+$/.test(v.codigo)) errores.codigo = 'Usa solo minúsculas, números, guiones y guiones bajos.'
  if (!v.ambito) errores.ambito = 'Selecciona el ámbito.'
  return errores
}

function campos(catalogo) {
  return (v) => {
    const lista = [
      { name: 'nombre', label: 'Nombre', required: true, ancho: 'mitad' },
      {
        name: 'codigo',
        label: 'Código',
        required: true,
        ancho: 'mitad',
        disabled: v.es_sistema,
        hint: v.es_sistema ? 'No se puede cambiar en un rol del sistema.' : 'Identificador interno, p. ej. "auditor".',
      },
      { name: 'ambito', label: 'Ámbito', type: 'select', options: AMBITOS, required: true, ancho: 'mitad', disabled: v.es_sistema },
    ]
    if (v.ambito === 'facultad' || v.ambito === 'cum_fum') {
      lista.push({ name: 'requiere_area', label: 'Sus usuarios se vinculan a un área (como los Jefes de Área)', type: 'checkbox' })
    }
    lista.push({ name: 'descripcion', label: 'Descripción', type: 'textarea', rows: 2 })
    lista.push({
      name: 'permisos',
      type: 'custom',
      render: (props) =>
        v.codigo === 'superadmin' ? (
          <Alert tone="info">El Superadmin tiene acceso total: no necesita permisos.</Alert>
        ) : (
          <MatrizPermisos catalogo={catalogo} {...props} />
        ),
    })
    return lista
  }
}

/** Roles del sistema y su matriz de permisos (RE-006). */
export function Roles() {
  const { tienePermiso } = useAuth()
  const [catalogo, setCatalogo] = useState([])

  useEffect(() => {
    roles.catalogo().then(setCatalogo, () => setCatalogo([]))
  }, [])

  return (
    <CrudPage
      titulo="Roles y permisos"
      subtitulo="Los 13 roles del sistema no se pueden eliminar ni cambiar de código o ámbito; sus permisos sí."
      singular="rol"
      recurso={roles}
      columnas={COLUMNAS}
      campos={campos(catalogo)}
      valoresIniciales={INICIALES}
      validar={validar}
      aFormulario={(r) => ({ ...INICIALES, ...r })}
      aDatos={({ nombre, codigo, ambito, requiere_area, descripcion, permisos }) => ({
        nombre,
        codigo,
        ambito,
        requiere_area: ambito !== 'global' && requiere_area,
        descripcion,
        permisos,
      })}
      puedeEliminarItem={(r) => !r.es_sistema}
      placeholderBusqueda="Nombre o código"
      permisos={{ crear: tienePermiso('roles.crear'), editar: tienePermiso('roles.editar'), eliminar: tienePermiso('roles.eliminar') }}
    />
  )
}
