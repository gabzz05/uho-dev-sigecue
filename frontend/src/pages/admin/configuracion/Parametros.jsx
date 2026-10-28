import { useCarga } from '../../../hooks/useCarga'
import { Input, useToast } from '../../../components/ui'
import { parametros } from '../../../services/configuracion'
import { SeccionFormulario } from './SeccionFormulario'

const LIMITES = {
  max_carreras_aspirante: [1, 10],
  login_max_intentos: [1, 20],
  login_bloqueo_minutos: [1, 1440],
  retencion_anios: [1, 20],
  retencion_otorgados_anios: [1, 30],
}

function validar(v) {
  const errores = {}
  Object.entries(LIMITES).forEach(([campo, [min, max]]) => {
    const n = Number(v[campo])
    if (!Number.isInteger(n) || n < min || n > max) errores[campo] = `Debe ser un número entre ${min} y ${max}.`
  })
  return errores
}

/** RF-007 y RF-008. */
export function Parametros({ editable }) {
  const carga = useCarga(parametros.obtener)
  const toast = useToast()

  return (
    <SeccionFormulario
      titulo="Parámetros del proceso"
      carga={carga}
      editable={editable}
      validar={validar}
      guardar={(v) => parametros.guardar(Object.fromEntries(Object.keys(LIMITES).map((campo) => [campo, v[campo]])))}
      onGuardado={() => toast.exito('Los parámetros se guardaron.')}
    >
      {({ campo }) => (
        <>
          <Input
            label="Máximo de carreras por aspirante"
            type="number"
            min={1}
            max={10}
            hint="Cuántas carreras puede seleccionar un aspirante en su solicitud (RF-007)."
            {...campo('max_carreras_aspirante')}
          />
          <span />
          <Input
            label="Intentos de inicio de sesión"
            type="number"
            min={1}
            max={20}
            hint="Intentos fallidos seguidos antes del bloqueo temporal."
            {...campo('login_max_intentos')}
          />
          <Input
            label="Duración del bloqueo (minutos)"
            type="number"
            min={1}
            max={1440}
            {...campo('login_bloqueo_minutos')}
          />
          <Input
            label="Retención de datos (años)"
            type="number"
            min={1}
            max={20}
            hint="No seleccionados, expresiones de interés y versiones antiguas de documentos (RG-028)."
            {...campo('retencion_anios')}
          />
          <Input
            label="Retención de otorgados (años)"
            type="number"
            min={1}
            max={30}
            hint="Conservación ampliada de quienes obtuvieron plaza."
            {...campo('retencion_otorgados_anios')}
          />
        </>
      )}
    </SeccionFormulario>
  )
}
