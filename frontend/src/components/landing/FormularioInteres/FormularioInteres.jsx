import { Check } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { useFormulario } from '../../../hooks/useFormulario'
import { publico } from '../../../services/publico'
import { MENSAJE_CELULAR, MENSAJE_CI, PATRON_CELULAR, PATRON_CI } from '../../../utils/validaciones'
import { Alert, Button, Checkbox, Input, Modal } from '../../ui'
import styles from './FormularioInteres.module.css'

const INICIALES = { nombre: '', ci: '', celular: '', email: '', acepta_privacidad: false }
const ID_FORMULARIO = 'formulario-interes'

function validar(v) {
  const errores = {}
  if (v.nombre.trim().split(/\s+/).length < 2) errores.nombre = 'Escribe tu nombre y apellidos.'
  if (!PATRON_CI.test(v.ci)) errores.ci = MENSAJE_CI
  if (!PATRON_CELULAR.test(v.celular)) errores.celular = MENSAJE_CELULAR
  if (!/^\S+@\S+\.\S+$/.test(v.email)) errores.email = 'Escribe un correo electrónico válido.'
  if (!v.acepta_privacidad) errores.acepta_privacidad = 'Debes aceptar la política de privacidad.'
  return errores
}

/** Expresión de interés sin registro (RF-021) para una oferta concreta. */
export function FormularioInteres({ oferta, convocatoria, onClose }) {
  const formulario = useFormulario(INICIALES)
  const { campo, checkbox, enviando, errorGeneral } = formulario
  const [mensaje, setMensaje] = useState('')

  async function enviar(evento) {
    evento.preventDefault()
    const respuesta = await formulario.enviar(
      (v) => publico.registrarInteres({ oferta: oferta.id, ...v, nombre: v.nombre.trim(), email: v.email.trim() }),
      validar,
    )
    if (respuesta) setMensaje(respuesta.mensaje)
  }

  return (
    <Modal
      open
      onClose={onClose}
      eyebrow="Expresión de interés"
      title={oferta.carrera.nombre}
      description={`${oferta.entidad.nombre} — ${oferta.entidad.municipio} · Curso ${convocatoria.anio_academico}`}
      footer={
        mensaje ? (
          <Button onClick={onClose}>Cerrar</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose} disabled={enviando}>
              Cancelar
            </Button>
            <Button type="submit" form={ID_FORMULARIO} variant="accent" icon={Check} loading={enviando}>
              Registrar interés
            </Button>
          </>
        )
      }
    >
      {mensaje ? (
        <Alert tone="success">{mensaje}</Alert>
      ) : (
        <form id={ID_FORMULARIO} className={styles.form} onSubmit={enviar} noValidate>
          <Alert tone="info">No necesitas registrarte. Deja tus datos y te avisaremos cuando abra la convocatoria oficial.</Alert>
          {errorGeneral && <Alert tone="danger">{errorGeneral}</Alert>}
          <Input label="Nombre completo" autoComplete="name" required {...campo('nombre')} />
          <div className={styles.fila}>
            <Input label="Carnet de identidad" inputMode="numeric" maxLength={11} hint="11 dígitos, sin espacios ni guiones" required {...campo('ci')} />
            <Input label="Celular" type="tel" inputMode="numeric" maxLength={8} hint="Ej: 55123456" required {...campo('celular')} />
          </div>
          <Input label="Correo electrónico" type="email" autoComplete="email" hint="Te escribiremos aquí cuando abra la convocatoria." required {...campo('email')} />
          <Checkbox
            label={
              <>
                Acepto que mis datos sean tratados conforme a la{' '}
                <Link to="/privacidad" target="_blank">
                  Política de Privacidad
                </Link>{' '}
                de la UHO para fines de gestión académica.
              </>
            }
            {...checkbox('acepta_privacidad')}
          />
        </form>
      )}
    </Modal>
  )
}
