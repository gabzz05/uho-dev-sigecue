import { useState } from 'react'
import { Button } from '../Button/Button'
import { ConfirmDialog } from '../ConfirmDialog/ConfirmDialog'

/** Botón que pide confirmación antes de ejecutar `onConfirm` (que puede ser asíncrono). */
export function BotonConfirmado({ titulo, mensaje, confirmLabel, tone = 'primary', onConfirm, children, ...props }) {
  const [abierto, setAbierto] = useState(false)
  const [ocupado, setOcupado] = useState(false)

  async function confirmar() {
    setOcupado(true)
    try {
      await onConfirm()
    } finally {
      setOcupado(false)
      setAbierto(false)
    }
  }

  return (
    <>
      <Button {...props} onClick={() => setAbierto(true)}>
        {children}
      </Button>
      <ConfirmDialog
        open={abierto}
        title={titulo}
        message={mensaje}
        confirmLabel={confirmLabel ?? titulo}
        tone={tone}
        loading={ocupado}
        onConfirm={confirmar}
        onCancel={() => setAbierto(false)}
      />
    </>
  )
}
