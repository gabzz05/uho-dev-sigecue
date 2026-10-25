import { useState } from 'react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { PageHeader, Tabs } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { areas, cargos, cumFum, departamentos, facultades, municipios } from '../../../services/nomencladores'
import { permisosNomenclador } from './permisos'

const TABS = [
  { id: 'areas', label: 'Áreas' },
  { id: 'departamentos', label: 'Departamentos' },
  { id: 'cargos', label: 'Cargos' },
  { id: 'municipios', label: 'Municipios' },
]

const COLUMNA_NOMBRE = { key: 'nombre', header: 'Nombre', render: (x) => <strong>{x.nombre}</strong> }
const CAMPO_NOMBRE = { name: 'nombre', label: 'Nombre', required: true }
const validarNombre = (v) => (v.nombre.trim() ? {} : { nombre: 'Escribe el nombre.' })

// La entidad de un área se elige en un solo select: "facultad:3" o "cum_fum:5".
const claveEntidad = (area) => (area.facultad ? `facultad:${area.facultad}` : `cum_fum:${area.cum_fum}`)

function datosArea({ nombre, entidad }) {
  if (!entidad) return { nombre }
  const [tipo, id] = entidad.split(':')
  return { nombre, facultad: tipo === 'facultad' ? id : null, cum_fum: tipo === 'cum_fum' ? id : null }
}

function Areas({ auth }) {
  const opcionesFacultad = useOpciones(auth.esGlobal ? facultades : null)
  const opcionesCum = useOpciones(auth.esGlobal ? cumFum : null)
  const entidades = [
    ...opcionesFacultad.map((o) => ({ value: `facultad:${o.value}`, label: o.label })),
    ...opcionesCum.map((o) => ({ value: `cum_fum:${o.value}`, label: o.label })),
  ]

  // Los roles locales crean áreas en su propia entidad: no eligen entidad.
  const campos = auth.esGlobal
    ? [CAMPO_NOMBRE, { name: 'entidad', label: 'Facultad o CUM/FUM', type: 'select', options: entidades, required: true }]
    : [CAMPO_NOMBRE]

  return (
    <CrudPage
      conEncabezado={false}
      singular="área"
      recurso={areas}
      columnas={[COLUMNA_NOMBRE, { key: 'entidad_nombre', header: 'Entidad' }]}
      campos={campos}
      valoresIniciales={{ nombre: '', entidad: '' }}
      validar={(v) => ({
        ...validarNombre(v),
        ...(auth.esGlobal && !v.entidad ? { entidad: 'Selecciona la entidad.' } : {}),
      })}
      aFormulario={(a) => ({ nombre: a.nombre, entidad: claveEntidad(a) })}
      aDatos={datosArea}
      permisos={permisosNomenclador(auth, { soloGlobales: false })}
    />
  )
}

function Departamentos({ auth }) {
  const opcionesArea = useOpciones(areas, { etiqueta: (a) => `${a.nombre} — ${a.entidad_nombre}` })
  return (
    <CrudPage
      conEncabezado={false}
      singular="departamento"
      recurso={departamentos}
      columnas={[COLUMNA_NOMBRE, { key: 'area_nombre', header: 'Área' }]}
      campos={[CAMPO_NOMBRE, { name: 'area', label: 'Área', type: 'select', options: opcionesArea, required: true }]}
      filtros={[{ name: 'area', label: 'Área', options: opcionesArea }]}
      valoresIniciales={{ nombre: '', area: '' }}
      validar={(v) => ({ ...validarNombre(v), ...(!v.area ? { area: 'Selecciona el área.' } : {}) })}
      aFormulario={(d) => ({ nombre: d.nombre, area: String(d.area) })}
      permisos={permisosNomenclador(auth, { soloGlobales: false })}
    />
  )
}

function Cargos({ auth }) {
  return (
    <CrudPage
      conEncabezado={false}
      singular="cargo"
      recurso={cargos}
      columnas={[COLUMNA_NOMBRE]}
      campos={[CAMPO_NOMBRE]}
      valoresIniciales={{ nombre: '' }}
      validar={validarNombre}
      aFormulario={(c) => ({ nombre: c.nombre })}
      permisos={permisosNomenclador(auth)}
    />
  )
}

function Municipios({ auth }) {
  return (
    <CrudPage
      conEncabezado={false}
      singular="municipio"
      recurso={municipios}
      columnas={[COLUMNA_NOMBRE, { key: 'provincia', header: 'Provincia' }]}
      campos={[
        { ...CAMPO_NOMBRE, ancho: 'mitad' },
        { name: 'provincia', label: 'Provincia', required: true, ancho: 'mitad' },
      ]}
      valoresIniciales={{ nombre: '', provincia: 'Holguín' }}
      validar={(v) => ({ ...validarNombre(v), ...(!v.provincia.trim() ? { provincia: 'Escribe la provincia.' } : {}) })}
      aFormulario={(m) => ({ nombre: m.nombre, provincia: m.provincia })}
      permisos={permisosNomenclador(auth)}
    />
  )
}

const PANELES = { areas: Areas, departamentos: Departamentos, cargos: Cargos, municipios: Municipios }

/** Áreas, departamentos, cargos y municipios (RF-003, RF-005, RF-006). */
export function OtrosNomencladores() {
  const auth = useAuth()
  const [tab, setTab] = useState('areas')
  const Panel = PANELES[tab]

  return (
    <>
      <PageHeader title="Otros nomencladores" />
      <Tabs tabs={TABS} activa={tab} onChange={setTab} label="Nomenclador">
        <Panel auth={auth} />
      </Tabs>
    </>
  )
}
