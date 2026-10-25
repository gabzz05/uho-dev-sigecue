import { Save } from 'lucide-react'
import { useFormulario } from '../../hooks/useFormulario'
import { Alert, Button, Modal } from '../ui'
import { CamposFormulario } from './CamposFormulario'

const ID_FORMULARIO = 'formulario-recurso'

/**
 * Alta o edición de un registro. Montarlo con una `key` distinta por registro
 * para que el formulario empiece limpio cada vez.
 */
export function RecursoModal({ open, titulo, campos, valoresIniciales, validar, onGuardar, onClose }) {
  const formulario = useFormulario(valoresIniciales)

  async function alEnviar(evento) {
    evento.preventDefault()
    const guardado = await formulario.enviar(onGuardar, validar)
    if (guardado) onClose(guardado)
  }

  return (
    <Modal
      open={open}
      onClose={() => onClose()}
      title={titulo}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={() => onClose()} disabled={formulario.enviando}>
            Cancelar
          </Button>
          <Button type="submit" form={ID_FORMULARIO} icon={Save} loading={formulario.enviando}>
            Guardar
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} onSubmit={alEnviar} noValidate>
        {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
        <CamposFormulario campos={campos} formulario={formulario} />
      </form>
    </Modal>
  )
}
