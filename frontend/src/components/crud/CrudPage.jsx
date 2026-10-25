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

/**
 * Pantalla de listado + alta/edición/baja de un recurso (nomencladores y similares).
 *
 * - `recurso`: cliente de `crearRecurso`.
 * - `columnas`: columnas de la tabla (se añaden "Estado" y "Acciones").
 * - `campos`: esquema del formulario (ver CamposFormulario).
 * - `filtros`: selects extra `[{ name, label, options }]`; buscar y estado van siempre.
 * - `permisos`: `{ crear, editar, eliminar }`. Sin permiso, la acción no se muestra.
 * - `aFormulario(item)` / `aDatos(valores)`: conversión entre API y formulario.
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
}) {
  const listado = useListado(recurso, { filtrosIniciales: { buscar: '', activo: '' } })
  const toast = useToast()
  const [edicion, setEdicion] = useState(null) // { item } | { item: null } para alta
  const [aEliminar, setAEliminar] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  async function cambiarEstado(item) {
    try {
      await recurso.actualizar(item.id, { activo: !item.activo })
      toast.exito(item.activo ? `Se desactivó: ${item.nombre}.` : `Se activó: ${item.nombre}.`)
      listado.recargar()
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  async function eliminar() {
    setOcupado(true)
    try {
      await recurso.eliminar(aEliminar.id)
      toast.exito(`Se eliminó: ${aEliminar.nombre}.`)
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
      toast.exito(edicion.item ? 'Los cambios se guardaron.' : `Se creó: ${guardado.nombre}.`)
      listado.recargar()
    }
    setEdicion(null)
  }

  const columnasCompletas = [
    ...columnas,
    {
      key: 'activo',
      header: 'Estado',
      render: (item) => <Badge tone={item.activo ? 'success' : 'neutral'}>{item.activo ? 'Activo' : 'Inactivo'}</Badge>,
    },
  ]
  if (permisos.editar || permisos.eliminar) {
    columnasCompletas.push({
      key: 'acciones',
      header: <span className={styles.srOnly}>Acciones</span>,
      align: 'right',
      render: (item) => (
        <div className={styles.acciones}>
          {permisos.editar && (
            <>
              <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEdicion({ item })} aria-label={`Editar ${item.nombre}`} />
              <Button
                variant="ghost"
                size="sm"
                icon={Power}
                onClick={() => cambiarEstado(item)}
                aria-label={item.activo ? `Desactivar ${item.nombre}` : `Activar ${item.nombre}`}
              />
            </>
          )}
          {permisos.eliminar && (
            <Button variant="ghost" size="sm" icon={Trash2} onClick={() => setAEliminar(item)} aria-label={`Eliminar ${item.nombre}`} />
          )}
        </div>
      ),
    })
  }

  const botonNuevo = permisos.crear && (
    <Button icon={Plus} onClick={() => setEdicion({ item: null })}>
      Nuevo(a) {singular}
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
            placeholder="Nombre o código"
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
          <Select
            label="Estado"
            placeholder="Todos"
            options={OPCIONES_ESTADO}
            value={listado.filtros.activo}
            onChange={(e) => listado.cambiarFiltro('activo', e.target.value)}
          />
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
          titulo={edicion.item ? `Editar ${singular}` : `Nuevo(a) ${singular}`}
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
        message={`¿Eliminar "${aEliminar?.nombre}"? Si está en uso no se podrá eliminar; en ese caso desactívalo.`}
        confirmLabel="Eliminar"
        loading={ocupado}
        onConfirm={eliminar}
        onCancel={() => setAEliminar(null)}
      />
    </>
  )
}
