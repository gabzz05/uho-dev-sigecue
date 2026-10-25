import { useState } from 'react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { Badge, PageHeader, Tabs } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { cumFum, facultades, municipios } from '../../../services/nomencladores'
import { omitirArchivoSinCambios } from '../../../services/recursos'
import { permisosNomenclador } from './permisos'

const TABS = [
  { id: 'facultades', label: 'Facultades' },
  { id: 'cum-fum', label: 'CUM / FUM' },
]

const TIPOS = [
  { value: 'CUM', label: 'CUM — Centro Universitario Municipal' },
  { value: 'FUM', label: 'FUM — Filial Universitaria Municipal' },
]

function validarEntidad(v) {
  const errores = {}
  if (!v.nombre.trim()) errores.nombre = 'Escribe el nombre.'
  if (!v.codigo.trim()) errores.codigo = 'Escribe el código.'
  if (!v.municipio) errores.municipio = 'Selecciona el municipio.'
  if ('tipo' in v && !v.tipo) errores.tipo = 'Selecciona si es CUM o FUM.'
  return errores
}

const aFormulario = (iniciales) => (item) => ({ ...iniciales, ...item, municipio: String(item.municipio), imagen: item.imagen ?? '' })

const COLUMNA_MUNICIPIO = { key: 'municipio_nombre', header: 'Municipio' }

function Facultades({ opcionesMunicipio, permisos }) {
  const iniciales = { nombre: '', codigo: '', decano: '', telefono: '', email: '', municipio: '', descripcion: '', imagen: '' }
  return (
    <CrudPage
      conEncabezado={false}
      singular="facultad"
      recurso={facultades}
      columnas={[
        { key: 'nombre', header: 'Facultad', render: (f) => <strong>{f.nombre}</strong> },
        { key: 'codigo', header: 'Código' },
        { key: 'decano', header: 'Decano(a)' },
        COLUMNA_MUNICIPIO,
      ]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true },
        { name: 'codigo', label: 'Código', required: true, ancho: 'mitad' },
        { name: 'municipio', label: 'Municipio', type: 'select', options: opcionesMunicipio, required: true, ancho: 'mitad' },
        { name: 'decano', label: 'Decano(a)', ancho: 'mitad' },
        { name: 'telefono', label: 'Teléfono', type: 'tel', ancho: 'mitad' },
        { name: 'email', label: 'Email institucional', type: 'email' },
        { name: 'descripcion', label: 'Descripción', type: 'textarea' },
        { name: 'imagen', label: 'Imagen', type: 'image' },
      ]}
      filtros={[{ name: 'municipio', label: 'Municipio', options: opcionesMunicipio }]}
      valoresIniciales={iniciales}
      validar={validarEntidad}
      aFormulario={aFormulario(iniciales)}
      aDatos={omitirArchivoSinCambios}
      permisos={permisos}
    />
  )
}

function CumsFums({ opcionesMunicipio, permisos }) {
  const iniciales = { nombre: '', codigo: '', tipo: '', director: '', telefono: '', email: '', municipio: '', imagen: '' }
  return (
    <CrudPage
      conEncabezado={false}
      singular="CUM/FUM"
      recurso={cumFum}
      columnas={[
        { key: 'nombre', header: 'Centro', render: (c) => <strong>{c.nombre}</strong> },
        { key: 'tipo', header: 'Tipo', render: (c) => <Badge tone="success">{c.tipo}</Badge> },
        { key: 'codigo', header: 'Código' },
        { key: 'director', header: 'Director(a)' },
        COLUMNA_MUNICIPIO,
      ]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true },
        { name: 'tipo', label: 'Tipo', type: 'select', options: TIPOS, required: true, ancho: 'mitad' },
        { name: 'codigo', label: 'Código', required: true, ancho: 'mitad' },
        { name: 'municipio', label: 'Municipio', type: 'select', options: opcionesMunicipio, required: true, ancho: 'mitad' },
        { name: 'director', label: 'Director(a)', ancho: 'mitad' },
        { name: 'telefono', label: 'Teléfono', type: 'tel', ancho: 'mitad' },
        { name: 'email', label: 'Email institucional', type: 'email', ancho: 'mitad' },
        { name: 'imagen', label: 'Imagen', type: 'image' },
      ]}
      filtros={[
        { name: 'tipo', label: 'Tipo', options: TIPOS.map((t) => ({ value: t.value, label: t.value })) },
        { name: 'municipio', label: 'Municipio', options: opcionesMunicipio },
      ]}
      valoresIniciales={iniciales}
      validar={validarEntidad}
      aFormulario={aFormulario(iniciales)}
      aDatos={omitirArchivoSinCambios}
      permisos={permisos}
    />
  )
}

/** Facultades y CUM/FUM (RF-001, RF-002). */
export function Entidades() {
  const auth = useAuth()
  const [tab, setTab] = useState('facultades')
  const opcionesMunicipio = useOpciones(municipios)
  const permisos = permisosNomenclador(auth)

  return (
    <>
      <PageHeader title="Facultades / CUM" subtitle="Entidades que ofertan carreras por encuentro." />
      <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Tipo de entidad">
        {tab === 'facultades' ? (
          <Facultades opcionesMunicipio={opcionesMunicipio} permisos={permisos} />
        ) : (
          <CumsFums opcionesMunicipio={opcionesMunicipio} permisos={permisos} />
        )}
      </Tabs>
    </>
  )
}
