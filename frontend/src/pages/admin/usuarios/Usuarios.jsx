import { LockOpen } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { CrudPage } from '../../../components/crud/CrudPage'
import { Badge, Button } from '../../../components/ui'
import { useAuth } from '../../../hooks/useAuth'
import { useOpciones } from '../../../hooks/useOpciones'
import { areas, cargos, cumFum, facultades } from '../../../services/nomencladores'
import { usuarios } from '../../../services/usuarios'
import { MENSAJE_CELULAR, MENSAJE_CI, PATRON_CELULAR, PATRON_CI } from '../../auth/validaciones'
import styles from './Usuarios.module.css'

const ORIGENES = [
  { value: 'local', label: 'Local (contraseña de SIGECUE)' },
  { value: 'sgu', label: 'SGU (auth.uho.edu.cu)' },
]

const INICIALES = {
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  ci: '',
  celular: '',
  rol: '',
  facultad: '',
  cum_fum: '',
  area: '',
  cargo: '',
  origen: 'local',
  password: '',
}

const nombreDe = (u) => `${u.first_name} ${u.last_name}`.trim() || u.username
const bloqueoTemporal = (u) => u.is_active && u.bloqueado_hasta && new Date(u.bloqueado_hasta) > new Date()
const aTexto = (valor) => (valor === null || valor === undefined ? '' : String(valor))
const aId = (valor) => (valor === '' ? null : valor)

/** Bloquear/desbloquear sustituye a activar/desactivar: los usuarios no se borran. */
const ESTADO_USUARIO = {
  activo: (u) => u.is_active,
  alternar: (_, u) => (u.is_active ? usuarios.bloquear(u.id) : usuarios.desbloquear(u.id)),
  etiquetas: { activo: 'Activo', inactivo: 'Bloqueado' },
  acciones: { desactivar: 'Bloquear', activar: 'Desbloquear' },
  mensajes: { desactivado: 'Se bloqueó', activado: 'Se desbloqueó' },
  render: (u) =>
    !u.is_active ? (
      <Badge tone="neutral">Bloqueado</Badge>
    ) : bloqueoTemporal(u) ? (
      <Badge tone="warning">Bloqueo temporal</Badge>
    ) : (
      <Badge tone="success">Activo</Badge>
    ),
}

function formatearFecha(iso) {
  return iso ? new Date(iso).toLocaleString('es-CU', { dateStyle: 'short', timeStyle: 'short' }) : 'Nunca'
}

/** Gestión de usuarios internos (RF-014 a RF-017). */
export function Usuarios() {
  const { tienePermiso, esGlobal, usuario: actual } = useAuth()
  const [rolesAsignables, setRolesAsignables] = useState([])
  const opcionesFacultad = useOpciones(esGlobal ? facultades : null)
  const opcionesCum = useOpciones(esGlobal ? cumFum : null)
  const opcionesArea = useOpciones(areas)
  const opcionesCargo = useOpciones(cargos)

  useEffect(() => {
    usuarios.rolesAsignables().then(setRolesAsignables, () => setRolesAsignables([]))
  }, [])

  const rolPorCodigo = useMemo(() => Object.fromEntries(rolesAsignables.map((r) => [r.codigo, r])), [rolesAsignables])
  const opcionesRol = rolesAsignables.map((r) => ({ value: r.codigo, label: r.nombre }))

  // La entidad de un usuario local que crea un rol local es siempre la suya.
  const entidadPropia = actual.entidad

  function areasDe(v) {
    const facultad = v.facultad || (entidadPropia?.tipo === 'facultad' ? String(entidadPropia.id) : '')
    const cum = v.cum_fum || (entidadPropia?.tipo === 'cum_fum' ? String(entidadPropia.id) : '')
    return opcionesArea.filter((o) =>
      facultad ? String(o.item.facultad) === facultad : cum ? String(o.item.cum_fum) === cum : false,
    )
  }

  function campos(v) {
    const rol = rolPorCodigo[v.rol]
    const editando = Boolean(v.id)
    const lista = [
      { name: 'first_name', label: 'Nombre', required: true, ancho: 'mitad' },
      { name: 'last_name', label: 'Apellidos', ancho: 'mitad' },
      { name: 'username', label: 'Nombre de usuario', required: true, ancho: 'mitad', disabled: editando, autoComplete: 'off' },
      { name: 'email', label: 'Correo electrónico', type: 'email', required: true, ancho: 'mitad' },
      { name: 'ci', label: 'Carnet de identidad', ancho: 'mitad', hint: 'Opcional. 11 dígitos.' },
      { name: 'celular', label: 'Celular', type: 'tel', ancho: 'mitad', hint: 'Opcional.' },
      { name: 'rol', label: 'Rol', type: 'select', options: opcionesRol, required: true, ancho: 'mitad' },
      { name: 'cargo', label: 'Cargo', type: 'select', options: opcionesCargo, placeholder: 'Sin cargo', ancho: 'mitad' },
    ]
    if (esGlobal && rol?.ambito === 'facultad') {
      lista.push({ name: 'facultad', label: 'Facultad', type: 'select', options: opcionesFacultad, required: true, ancho: 'mitad' })
    }
    if (esGlobal && rol?.ambito === 'cum_fum') {
      lista.push({ name: 'cum_fum', label: 'CUM/FUM', type: 'select', options: opcionesCum, required: true, ancho: 'mitad' })
    }
    if (rol?.requiere_area) {
      lista.push({ name: 'area', label: 'Área', type: 'select', options: areasDe(v), required: true, ancho: 'mitad' })
    }
    lista.push({ name: 'origen', label: 'Autenticación', type: 'select', options: ORIGENES, ancho: 'mitad' })
    if (v.origen === 'local') {
      lista.push({
        name: 'password',
        label: editando ? 'Nueva contraseña' : 'Contraseña',
        type: 'password',
        required: !editando,
        ancho: 'mitad',
        autoComplete: 'new-password',
        hint: editando ? 'Déjala vacía para no cambiarla.' : 'Mínimo 8 caracteres.',
      })
    }
    return lista
  }

  function validar(v) {
    const errores = {}
    const rol = rolPorCodigo[v.rol]
    if (!v.first_name.trim()) errores.first_name = 'Escribe el nombre.'
    if (!v.username.trim()) errores.username = 'Escribe el nombre de usuario.'
    if (!/^\S+@\S+\.\S+$/.test(v.email)) errores.email = 'Escribe un correo electrónico válido.'
    if (v.ci && !PATRON_CI.test(v.ci)) errores.ci = MENSAJE_CI
    if (v.celular && !PATRON_CELULAR.test(v.celular)) errores.celular = MENSAJE_CELULAR
    if (!rol) errores.rol = 'Selecciona el rol.'
    if (esGlobal && rol?.ambito === 'facultad' && !v.facultad) errores.facultad = 'Selecciona la Facultad.'
    if (esGlobal && rol?.ambito === 'cum_fum' && !v.cum_fum) errores.cum_fum = 'Selecciona el CUM/FUM.'
    if (rol?.requiere_area && !v.area) errores.area = 'Selecciona el área.'
    if (v.origen === 'local' && !v.id && v.password.length < 8) errores.password = 'La contraseña debe tener al menos 8 caracteres.'
    return errores
  }

  function aDatos(v) {
    const rol = rolPorCodigo[v.rol]
    const datos = {
      username: v.username.trim(),
      first_name: v.first_name.trim(),
      last_name: v.last_name.trim(),
      email: v.email.trim(),
      ci: v.ci,
      celular: v.celular,
      rol: v.rol,
      cargo: aId(v.cargo),
      area: rol?.requiere_area ? aId(v.area) : null,
      origen: v.origen,
    }
    // Un rol local que no es global no envía entidad: la API usa la suya.
    if (esGlobal) {
      datos.facultad = rol?.ambito === 'facultad' ? aId(v.facultad) : null
      datos.cum_fum = rol?.ambito === 'cum_fum' ? aId(v.cum_fum) : null
    }
    if (v.origen === 'local' && v.password) datos.password = v.password
    return datos
  }

  const columnas = [
    {
      key: 'usuario',
      header: 'Usuario',
      render: (u) => (
        <div className={styles.persona}>
          <strong>{nombreDe(u)}</strong>
          <small>
            {u.username} · {u.email}
          </small>
        </div>
      ),
    },
    { key: 'rol', header: 'Rol', render: (u) => rolPorCodigo[u.rol]?.nombre ?? u.rol },
    { key: 'entidad', header: 'Entidad', render: (u) => u.entidad?.nombre ?? <Badge tone="primary">Global</Badge> },
    { key: 'area_nombre', header: 'Área', render: (u) => u.area_nombre ?? '—' },
    { key: 'last_login', header: 'Último acceso', render: (u) => formatearFecha(u.last_login) },
  ]

  return (
    <CrudPage
      titulo="Usuarios"
      subtitulo={
        esGlobal
          ? 'Usuarios internos de todas las entidades. Los aspirantes se gestionan en Solicitudes.'
          : `Usuarios internos de ${entidadPropia?.nombre ?? 'tu entidad'}.`
      }
      singular="usuario"
      recurso={usuarios}
      columnas={columnas}
      campos={campos}
      filtros={[{ name: 'rol', label: 'Rol', options: opcionesRol }]}
      valoresIniciales={INICIALES}
      validar={validar}
      aFormulario={(u) => ({
        ...INICIALES,
        ...Object.fromEntries(Object.keys(INICIALES).map((k) => [k, aTexto(u[k])])),
        id: u.id,
        origen: u.origen,
        password: '',
      })}
      aDatos={aDatos}
      nombreDe={nombreDe}
      estado={ESTADO_USUARIO}
      placeholderBusqueda="Usuario, nombre o apellidos"
      accionesExtra={(u, recargar) =>
        tienePermiso('usuarios.editar') &&
        bloqueoTemporal(u) && (
          <Button
            variant="ghost"
            size="sm"
            icon={LockOpen}
            aria-label={`Levantar bloqueo temporal de ${nombreDe(u)}`}
            onClick={() => usuarios.desbloquear(u.id).then(recargar)}
          />
        )
      }
      permisos={{ crear: tienePermiso('usuarios.crear'), editar: tienePermiso('usuarios.editar'), eliminar: false }}
    />
  )
}
