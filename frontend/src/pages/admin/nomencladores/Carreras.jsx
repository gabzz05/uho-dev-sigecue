import { CrudPage } from '../../../components/crud/CrudPage'
import { useAuth } from '../../../hooks/useAuth'
import { carreras } from '../../../services/nomencladores'
import { omitirArchivoSinCambios } from '../../../services/recursos'
import { permisosNomenclador } from './permisos'

const CAMPOS = [
  { name: 'nombre', label: 'Nombre', required: true },
  { name: 'codigo', label: 'Código', required: true, ancho: 'mitad' },
  { name: 'duracion_anios', label: 'Duración (años)', type: 'number', min: 1, max: 8, required: true, ancho: 'mitad' },
  { name: 'descripcion', label: 'Descripción', type: 'textarea' },
  { name: 'objetivo', label: 'Objetivo', type: 'textarea' },
  { name: 'perfil_egresado', label: 'Perfil del egresado', type: 'textarea' },
  { name: 'requisitos', label: 'Requisitos de ingreso', type: 'textarea' },
  { name: 'imagen', label: 'Imagen', type: 'image' },
]

const INICIALES = {
  nombre: '',
  codigo: '',
  duracion_anios: '',
  descripcion: '',
  objetivo: '',
  perfil_egresado: '',
  requisitos: '',
  imagen: '',
}

const COLUMNAS = [
  { key: 'nombre', header: 'Carrera', render: (c) => <strong>{c.nombre}</strong> },
  { key: 'codigo', header: 'Código' },
  { key: 'duracion_anios', header: 'Duración', align: 'center', render: (c) => `${c.duracion_anios} años` },
  { key: 'modalidad_nombre', header: 'Modalidad' },
]

const FILTROS = [
  {
    name: 'duracion',
    label: 'Duración',
    options: [4, 5, 6].map((n) => ({ value: String(n), label: `${n} años` })),
  },
]

function validar(v) {
  const errores = {}
  if (!v.nombre.trim()) errores.nombre = 'Escribe el nombre de la carrera.'
  if (!v.codigo.trim()) errores.codigo = 'Escribe el código.'
  const duracion = Number(v.duracion_anios)
  if (!Number.isInteger(duracion) || duracion < 1 || duracion > 8) errores.duracion_anios = 'Indica una duración entre 1 y 8 años.'
  return errores
}

/** Catálogo global de carreras (RF-004). */
export function Carreras() {
  const auth = useAuth()
  return (
    <CrudPage
      titulo="Carreras"
      subtitulo="Catálogo global de carreras por encuentro. La oferta de cada entidad se define en cada convocatoria."
      singular="carrera"
      recurso={carreras}
      columnas={COLUMNAS}
      campos={CAMPOS}
      filtros={FILTROS}
      valoresIniciales={INICIALES}
      validar={validar}
      aFormulario={(c) => ({ ...INICIALES, ...c, imagen: c.imagen ?? '' })}
      aDatos={omitirArchivoSinCambios}
      permisos={permisosNomenclador(auth)}
    />
  )
}
