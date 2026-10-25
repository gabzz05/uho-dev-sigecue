import { Eye, RotateCcw, Save } from 'lucide-react'
import { useState } from 'react'
import { useCarga } from '../../../hooks/useCarga'
import { useFormulario } from '../../../hooks/useFormulario'
import { Alert, Button, Card, CardBody, CardHeader, ConfirmDialog, Input, Spinner, Textarea, useToast } from '../../../components/ui'
import { plantillas } from '../../../services/configuracion'
import { mensajeDeError } from '../../../services/errores'
import styles from './Configuracion.module.css'

const PATRON_VARIABLE = /{{\s*(\w+)\s*}}/g

/** Variables usadas que la plantilla no admite (misma regla que la API). */
function desconocidas(texto, permitidas) {
  return [...new Set([...texto.matchAll(PATRON_VARIABLE)].map((m) => m[1]))].filter((v) => !(v in permitidas))
}

function Editor({ plantilla, editable, onGuardada }) {
  const formulario = useFormulario({ asunto: plantilla.asunto, cuerpo: plantilla.cuerpo })
  const [vista, setVista] = useState(null)
  const [confirmar, setConfirmar] = useState(false)
  const toast = useToast()

  function validar(v) {
    const errores = {}
    if (!v.asunto.trim()) errores.asunto = 'Escribe el asunto.'
    if (!v.cuerpo.trim()) errores.cuerpo = 'Escribe el cuerpo del correo.'
    for (const campo of ['asunto', 'cuerpo']) {
      const malas = desconocidas(v[campo], plantilla.variables)
      if (malas.length) errores[campo] = `Variables no disponibles en esta plantilla: ${malas.join(', ')}.`
    }
    return errores
  }

  async function guardar(evento) {
    evento.preventDefault()
    const guardada = await formulario.enviar((v) => plantillas.guardar(plantilla.codigo, v), validar)
    if (guardada) {
      toast.exito('La plantilla se guardó.')
      onGuardada(guardada)
    }
  }

  async function verVistaPrevia() {
    try {
      setVista(await plantillas.vistaPrevia(plantilla.codigo, formulario.valores))
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  async function restablecer() {
    setConfirmar(false)
    try {
      const restablecida = await plantillas.restablecer(plantilla.codigo)
      formulario.setValores({ asunto: restablecida.asunto, cuerpo: restablecida.cuerpo })
      toast.exito('Se restableció el texto por defecto.')
      onGuardada(restablecida)
    } catch (error) {
      toast.error(mensajeDeError(error))
    }
  }

  return (
    <Card>
      <CardHeader title={plantilla.nombre} />
      <CardBody>
        <form className={styles.form} onSubmit={guardar} noValidate>
          {plantilla.descripcion && <p className={styles.descripcion}>{plantilla.descripcion}</p>}
          <div className={styles.variables} aria-label="Variables disponibles">
            Variables disponibles:
            {Object.entries(plantilla.variables).map(([nombre, descripcion]) => (
              <code key={nombre} title={descripcion}>
                {`{{ ${nombre} }}`}
              </code>
            ))}
          </div>
          {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
          <Input label="Asunto" disabled={!editable} {...formulario.campo('asunto')} />
          <Textarea label="Cuerpo" rows={12} disabled={!editable} {...formulario.campo('cuerpo')} />
          {vista && (
            <div className={styles.vistaPrevia} aria-label="Vista previa">
              <strong>{vista.asunto}</strong>
              {vista.cuerpo}
            </div>
          )}
          <div className={styles.pie}>
            <Button variant="secondary" icon={Eye} onClick={verVistaPrevia}>
              Vista previa
            </Button>
            {editable && (
              <>
                <Button variant="ghost" icon={RotateCcw} onClick={() => setConfirmar(true)}>
                  Restablecer
                </Button>
                <Button type="submit" icon={Save} loading={formulario.enviando}>
                  Guardar
                </Button>
              </>
            )}
          </div>
        </form>
      </CardBody>
      <ConfirmDialog
        open={confirmar}
        title="Restablecer plantilla"
        message="Se perderá el texto actual y se usará el texto por defecto del sistema."
        confirmLabel="Restablecer"
        tone="primary"
        onConfirm={restablecer}
        onCancel={() => setConfirmar(false)}
      />
    </Card>
  )
}

/** Plantillas de correo (RF-011). */
export function Plantillas({ editable }) {
  const carga = useCarga(plantillas.listar)

  if (carga.cargando) return <Spinner label="Cargando las plantillas" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>
  return <ListaPlantillas iniciales={carga.datos} editable={editable} />
}

function ListaPlantillas({ iniciales, editable }) {
  const [lista, setLista] = useState(iniciales)
  const [seleccionada, setSeleccionada] = useState(iniciales[0]?.codigo ?? null)

  const plantilla = lista.find((p) => p.codigo === seleccionada)
  const actualizar = (nueva) => setLista((actuales) => actuales.map((p) => (p.codigo === nueva.codigo ? nueva : p)))

  return (
    <div className={styles.plantillas}>
      <ul className={styles.lista} aria-label="Plantillas">
        {lista.map((p) => (
          <li key={p.codigo}>
            <button
              type="button"
              className={styles.opcion}
              aria-current={p.codigo === seleccionada}
              onClick={() => setSeleccionada(p.codigo)}
            >
              <strong>{p.nombre}</strong>
              <span>{p.asunto}</span>
            </button>
          </li>
        ))}
      </ul>
      {plantilla && <Editor key={plantilla.codigo} plantilla={plantilla} editable={editable} onGuardada={actualizar} />}
    </div>
  )
}
