import { Save } from 'lucide-react'
import { useFormulario } from '../../../hooks/useFormulario'
import { Alert, Button, Card, CardBody, CardHeader, Spinner } from '../../../components/ui'
import styles from './Configuracion.module.css'

/**
 * Tarjeta con un formulario de configuración que se carga y se guarda contra la API.
 * `children(formulario)` pinta los campos. Sin `editable` todo queda en solo lectura.
 */
export function SeccionFormulario({ titulo, descripcion, carga, guardar, validar, editable, onGuardado, acciones, children }) {
  if (carga.cargando) return <Spinner label="Cargando la configuración" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>
  return (
    <Formulario
      titulo={titulo}
      descripcion={descripcion}
      iniciales={carga.datos}
      guardar={guardar}
      validar={validar}
      editable={editable}
      onGuardado={onGuardado}
      acciones={acciones}
    >
      {children}
    </Formulario>
  )
}

function Formulario({ titulo, descripcion, iniciales, guardar, validar, editable, onGuardado, acciones, children }) {
  const formulario = useFormulario(iniciales)

  async function alEnviar(evento) {
    evento.preventDefault()
    const guardado = await formulario.enviar(guardar, validar)
    if (guardado) {
      formulario.setValores(guardado)
      onGuardado?.(guardado)
    }
  }

  return (
    <Card>
      <CardHeader title={titulo} />
      <CardBody>
        {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
        <form onSubmit={alEnviar} noValidate className={styles.form}>
          {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
          <fieldset disabled={!editable || formulario.enviando} className={styles.fieldset}>
            {children(formulario)}
          </fieldset>
          <div className={styles.pie}>
            {acciones?.(formulario)}
            {editable && (
              <Button type="submit" icon={Save} loading={formulario.enviando}>
                Guardar
              </Button>
            )}
          </div>
        </form>
      </CardBody>
    </Card>
  )
}
