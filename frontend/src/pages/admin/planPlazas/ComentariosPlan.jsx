import { Send } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Alert, Button, EmptyState, Spinner, Textarea, useToast } from '../../../components/ui'
import { useCarga } from '../../../hooks/useCarga'
import { useFormulario } from '../../../hooks/useFormulario'
import { planes } from '../../../services/planPlazas'
import { formatearFechaHora } from '../../../utils/fechas'
import styles from './Plan.module.css'

function Lista({ plan, iniciales, puedeComentar }) {
  const toast = useToast()
  const [lista, setLista] = useState(iniciales)
  const formulario = useFormulario({ texto: '' })

  async function comentar(evento) {
    evento.preventDefault()
    const nuevo = await formulario.enviar(
      (v) => planes.comentar(plan.id, v.texto.trim()),
      (v) => (v.texto.trim() ? {} : { texto: 'Escribe el comentario.' }),
    )
    if (nuevo) {
      setLista((actual) => [...actual, nuevo])
      formulario.setValores({ texto: '' })
      toast.exito('Comentario publicado.')
    }
  }

  return (
    <div className={styles.pila}>
      {lista.length === 0 ? (
        <EmptyState title="Sin comentarios" message="Aquí se ven las observaciones sobre el plan de tu entidad." />
      ) : (
        <ul className={styles.comentarios}>
          {lista.map((c) => (
            <li key={c.id}>
              <header>
                <strong>{c.usuario_nombre}</strong>
                <time dateTime={c.created_at}>{formatearFechaHora(c.created_at)}</time>
              </header>
              {(c.linea_descripcion || c.entidad) && <small>{c.linea_descripcion || c.entidad?.nombre}</small>}
              <p>{c.texto}</p>
            </li>
          ))}
        </ul>
      )}
      {puedeComentar && (
        <form onSubmit={comentar} noValidate className={styles.pila}>
          {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
          <Textarea label="Nuevo comentario" rows={3} {...formulario.campo('texto')} />
          <div>
            <Button type="submit" icon={Send} loading={formulario.enviando}>
              Comentar
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

/** Comentarios sobre el plan (los Jefes de Área ven y comentan, pero no responden). */
export function ComentariosPlan({ plan }) {
  const carga = useCarga(useCallback(() => planes.comentarios(plan.id), [plan.id]))
  if (carga.cargando) return <Spinner label="Cargando comentarios" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>
  return <Lista plan={plan} iniciales={carga.datos} puedeComentar={plan.acciones.includes('comentar')} />
}
