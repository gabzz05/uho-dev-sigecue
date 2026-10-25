import { useCarga } from '../../../hooks/useCarga'
import { useIdentidad } from '../../../hooks/useIdentidad'
import { ImageInput, Input, useToast } from '../../../components/ui'
import { identidad as servicio } from '../../../services/configuracion'
import { omitirArchivoSinCambios } from '../../../services/recursos'
import styles from './Configuracion.module.css'
import { SeccionFormulario } from './SeccionFormulario'

const COLORES = [
  { campo: 'color_primario', label: 'Color primario', hint: 'Cabeceras, menú lateral y botones principales.' },
  { campo: 'color_primario_claro', label: 'Color primario claro', hint: 'Enlaces, foco y degradados.' },
  { campo: 'color_acento', label: 'Color de acento', hint: 'Acciones destacadas y marcas activas.' },
]
const PATRON_COLOR = /^#[0-9A-Fa-f]{6}$/

function validar(v) {
  const errores = {}
  if (!v.nombre_institucion.trim()) errores.nombre_institucion = 'Escribe el nombre de la institución.'
  COLORES.forEach(({ campo }) => {
    if (!PATRON_COLOR.test(v[campo])) errores[campo] = 'Usa un color hexadecimal, p. ej. #1A3A6B.'
  })
  return errores
}

function datos(v) {
  const { nombre_institucion, color_primario, color_primario_claro, color_acento, escudo } = v
  return omitirArchivoSinCambios({ nombre_institucion, color_primario, color_primario_claro, color_acento, escudo: escudo ?? '' }, 'escudo')
}

/** Identidad visual (RE-001): se aplica a toda la interfaz al guardar. */
export function Identidad({ editable }) {
  const carga = useCarga(servicio.obtener)
  const { actualizar } = useIdentidad()
  const toast = useToast()

  return (
    <SeccionFormulario
      titulo="Identidad visual"
      descripcion="Nombre, colores institucionales y escudo. El escudo aparece en la interfaz y en los PDF."
      carga={carga}
      editable={editable}
      validar={validar}
      guardar={(v) => servicio.guardar(datos(v))}
      onGuardado={(guardada) => {
        actualizar(guardada)
        toast.exito('La identidad visual se guardó y ya se aplica.')
      }}
    >
      {({ campo, valores, setValores, errores }) => (
        <>
          <Input label="Nombre de la institución" className={styles.completo} {...campo('nombre_institucion')} />
          {COLORES.map(({ campo: nombre, label, hint }) => (
            <div key={nombre} className={styles.color}>
              <Input label={label} hint={hint} maxLength={7} {...campo(nombre)} />
              <input
                type="color"
                className={styles.muestra}
                aria-label={`Elegir ${label.toLowerCase()}`}
                value={PATRON_COLOR.test(valores[nombre]) ? valores[nombre] : '#000000'}
                onChange={(e) => setValores((v) => ({ ...v, [nombre]: e.target.value.toUpperCase() }))}
              />
            </div>
          ))}
          <div className={styles.completo}>
            <ImageInput
              label="Escudo"
              value={valores.escudo ?? ''}
              error={errores.escudo}
              onChange={(escudo) => setValores((v) => ({ ...v, escudo }))}
            />
          </div>
        </>
      )}
    </SeccionFormulario>
  )
}
