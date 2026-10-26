import { Pencil, Plus, Power, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useListado } from '../../hooks/useListado'
import { mensajeDeError } from '../../services/errores'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  Input,
  PageHeader,
  Pagination,
  Select,
  TableFooter,
  Toolbar,
  useToast,
} from '../ui'
import styles from './Crud.module.css'
import { RecursoModal } from './RecursoModal'

const OPCIONES_ESTADO = [
  { value: 'true', label: 'Activos' },
  { value: 'false', label: 'Inactivos' },
]

const identidad = (x) => x
const porNombre = (item) => item.nombre
const siempre = () => true

/** Estado por defecto: campo `activo` editable con PATCH. */
const ESTADO_ACTIVO = {
  activo: (item) => item.activo,
  alternar: (recurso, item) => recurso.actualizar(item.id, { activo: !item.activo }),
  etiquetas: { activo: 'Activo', inactivo: 'Inactivo' },
  acciones: { desactivar: 'Desactivar', activar: 'Activar' },
  mensajes: { desactivado: 'Se desactivó', activado: 'Se activó' },
}

/**
 * Pantalla de listado + alta/edición/baja de un recurso (nomencladores y similares).
 *
 * - `recurso`: cliente de `crearRecurso`.
 * - `columnas`: columnas de la tabla (se añaden "Estado" y "Acciones").
 * - `campos`: esquema del formulario (ver CamposFormulario).
 * - `filtros`: selects extra `[{ name, label, options }]`; buscar y estado van siempre.
 * - `permisos`: `{ crear, editar, eliminar }`. Sin permiso, la acción no se muestra.
 * - `aFormulario(item)` / `aDatos(valores)`: conversión entre API y formulario.
 * - `nombreDe(item)`: texto con el que se nombra un registro en avisos y etiquetas.
 * - `estado`: cómo se lee y se alterna el estado (por defecto, el campo `activo`).
 *   `null` si el recurso no tiene estado activo/inactivo: sin columna, filtro ni botón.
 * - `etiquetaNuevo`: texto del botón y del título de alta (por defecto "Nuevo(a) {singular}").
 * - `filtrosFijos`: parámetros que se envían siempre al listar (p. ej. `{ convocatoria: 3 }`).
 * - `accionesExtra(item, recargar)`: botones adicionales por fila.
 * - `puedeEliminarItem(item)` / `puedeEditarItem(item)`: ocultan esas acciones en registros concretos.
 */
export function CrudPage({
  titulo,
  subtitulo,
  singular,
  recurso,
  columnas,
  campos,
  filtros = [],
  valoresIniciales,
  validar,
  permisos = {},
  aFormulario = identidad,
  aDatos = identidad,
  conEncabezado = true,
  nombreDe = porNombre,
  estado = ESTADO_ACTIVO,
  accionesExtra,
  puedeEliminarItem = siempre,
  puedeEditarItem = siempre,
  placeholderBusqueda = 'Nombre o código',
  filtrosFijos = {},
  etiquetaNuevo,
}) {
  const textoNuevo = etiquetaNuevo ?? `Nuevo(a) ${singular}`
  const conEstado = estado !== null
  const listado = useListado(recurso, {
    filtrosIniciales: { buscar: '', ...(conEstado ? { activo: '' } : {}), ...filtrosFijos },
  })
  const toast = useToast()
  const [edicion, setEdicion] = useState(null) // { item } | { item: null } para alta
  const [aEliminar, setAEliminar] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  async function cambiarEstado(item) {
    const activo = estado.activo(item)
    try {
      await estado.alternar(recurso, item)
      toast.exito(`${activo ? estado.mensajes.desactivado : estado.mensajes.activado}: ${nombreDe(item)}.`)
      listado.recargar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  async function eliminar() {
    setOcupado(true)
    try {
      await recurso.eliminar(aEliminar.id)
      toast.exito(`Se eliminó: ${nombreDe(aEliminar)}.`)
      listado.recargar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    } finally {
      setOcupado(false)
      setAEliminar(null)
    }
  }

  function guardar(valores) {
    const datos = aDatos(valores)
    return edicion.item ? recurso.actualizar(edicion.item.id, datos) : recurso.crear(datos)
  }

  function cerrarEdicion(guardado) {
    if (guardado) {
      toast.exito(edicion.item ? 'Los cambios se guardaron.' : `Se creó: ${nombreDe(guardado)}.`)
      listado.recargar()
    }
    setEdicion(null)
  }

  const columnasCompletas = [...columnas]
  if (conEstado) {
    columnasCompletas.push({
      key: 'activo',
      header: 'Estado',
      render: (item) =>
        estado.render?.(item) ?? (
          <Badge tone={estado.activo(item) ? 'success' : 'neutral'}>
            {estado.activo(item) ? estado.etiquetas.activo : estado.etiquetas.inactivo}
          </Badge>
        ),
    })
  }
  if (permisos.editar || permisos.eliminar || accionesExtra) {
    columnasCompletas.push({
      key: 'acciones',
      header: <span className={styles.srOnly}>Acciones</span>,
      align: 'right',
      render: (item) => (
        <div className={styles.acciones}>
          {accionesExtra?.(item, listado.recargar)}
          {permisos.editar && puedeEditarItem(item) && (
            <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEdicion({ item })} aria-label={`Editar ${nombreDe(item)}`} />
          )}
          {permisos.editar && conEstado && (
            <Button
              variant="ghost"
              size="sm"
              icon={Power}
              onClick={() => cambiarEstado(item)}
              aria-label={`${estado.activo(item) ? estado.acciones.desactivar : estado.acciones.activar} ${nombreDe(item)}`}
            />
          )}
          {permisos.eliminar && puedeEliminarItem(item) && (
            <Button
              variant="ghost"
              size="sm"
              icon={Trash2}
              onClick={() => setAEliminar(item)}
              aria-label={`Eliminar ${nombreDe(item)}`}
            />
          )}
        </div>
      ),
    })
  }

  const botonNuevo = permisos.crear && (
    <Button icon={Plus} onClick={() => setEdicion({ item: null })}>
      {textoNuevo}
    </Button>
  )

  return (
    <>
      {conEncabezado ? (
        <PageHeader title={titulo} subtitle={subtitulo} actions={botonNuevo} />
      ) : (
        botonNuevo && <div className={styles.accionesSuperiores}>{botonNuevo}</div>
      )}

      <Card>
        <Toolbar>
          <Input
            label="Buscar"
            type="search"
            placeholder={placeholderBusqueda}
            value={listado.filtros.buscar}
            onChange={(e) => listado.cambiarFiltro('buscar', e.target.value)}
          />
          {filtros.map((f) => (
            <Select
              key={f.name}
              label={f.label}
              placeholder="Todos"
              options={f.options}
              value={listado.filtros[f.name] ?? ''}
              onChange={(e) => listado.cambiarFiltro(f.name, e.target.value)}
            />
          ))}
          {conEstado && (
            <Select
              label="Estado"
              placeholder="Todos"
              options={OPCIONES_ESTADO}
              value={listado.filtros.activo}
              onChange={(e) => listado.cambiarFiltro('activo', e.target.value)}
            />
          )}
        </Toolbar>
        {listado.error && (
          <div className={styles.error}>
            <Alert tone="danger">{listado.error}</Alert>
          </div>
        )}
        <DataTable columns={columnasCompletas} rows={listado.filas} loading={listado.cargando} />
        <TableFooter>
          <Pagination page={listado.pagina} count={listado.total} pageSize={listado.pageSize} onChange={listado.setPagina} />
        </TableFooter>
      </Card>

      {edicion && (
        <RecursoModal
          key={edicion.item?.id ?? 'nuevo'}
          open
          titulo={edicion.item ? `Editar ${singular}` : textoNuevo}
          campos={campos}
          valoresIniciales={edicion.item ? aFormulario(edicion.item) : valoresIniciales}
          validar={validar}
          onGuardar={guardar}
          onClose={cerrarEdicion}
        />
      )}

      <ConfirmDialog
        open={Boolean(aEliminar)}
        title={`Eliminar ${singular}`}
        message={`¿Eliminar "${aEliminar ? nombreDe(aEliminar) : ''}"? Si está en uso no se podrá eliminar; en ese caso desactívalo.`}
        confirmLabel="Eliminar"
        loading={ocupado}
        onConfirm={eliminar}
        onCancel={() => setAEliminar(null)}
      />
    </>
  )
}
