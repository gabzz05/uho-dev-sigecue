import { ArrowRight, CheckCircle2, Circle, Eye, Save, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { Alert, Badge, Button, Card, CardBody, CardHeader, ImageInput, Input, PageHeader, Spinner, useToast } from '../../components/ui'
import { useArchivoPrivado } from '../../hooks/useArchivoPrivado'
import { useAuth } from '../../hooks/useAuth'
import { useCarga } from '../../hooks/useCarga'
import { useFormulario } from '../../hooks/useFormulario'
import { obtenerArchivo, perfilAspirante } from '../../services/aspirante'
import { mensajeDeError } from '../../services/errores'
import { actualizarPerfil } from '../../services/perfil'
import { FORMATOS_DOCUMENTO, formatearTamano } from '../../utils/archivos'
import { formatearFechaHora } from '../../utils/fechas'
import styles from './Aspirante.module.css'

/**
 * ¿Se puede cambiar ese elemento? Con el perfil congelado, solo lo que tiene
 * una observación por corregir (desbloqueo selectivo).
 */
function editable(perfil, objetivo, tipoDocumento = null) {
  if (!perfil.bloqueado) return true
  return perfil.a_corregir.some((a) => a.objetivo === objetivo && (a.tipo_documento ?? null) === tipoDocumento)
}

/** Completar perfil (RF-046): datos, foto y documentos que se exigen antes de elegir carreras. */
export function CompletarPerfil() {
  const carga = useCarga(perfilAspirante.obtener)
  const [actualizado, setActualizado] = useState(null)
  const perfil = actualizado ?? carga.datos

  if (carga.cargando) return <Spinner label="Cargando tu perfil" />
  if (carga.error) return <Alert tone="danger">{carga.error}</Alert>

  const recargar = () => perfilAspirante.obtener().then(setActualizado)
  const { listo_para_carreras: listo, cuota_usada: usada, cuota_maxima: maxima } = perfil.limites

  return (
    <>
      <PageHeader title="Completar perfil" subtitle="Antes de seleccionar carreras necesitas tus datos, tu foto y tus documentos." />
      <div className={styles.pila}>
        {perfil.bloqueado && perfil.a_corregir.length === 0 && (
          <Alert tone="info" title="Perfil congelado">
            La convocatoria en la que presentaste tu solicitud ya cerró. Puedes consultar tus datos, pero no modificarlos.
          </Alert>
        )}
        {perfil.a_corregir.length > 0 && (
          <Alert
            tone="warning"
            title="Tienes observaciones por corregir"
            action={
              <Button as={Link} to="/aspirante/solicitud" size="sm" icon={ArrowRight}>
                Ver observaciones
              </Button>
            }
          >
            {perfil.bloqueado ? 'Solo puedes cambiar lo observado. ' : ''}
            Cuando lo corrijas, pulsa «Enviar corrección» en Mi solicitud.
          </Alert>
        )}
        {listo && !perfil.bloqueado && (
          <Alert
            tone="success"
            title="Tu perfil está listo"
            action={
              <Button as={Link} to="/aspirante/solicitud" size="sm" icon={ArrowRight}>
                Seleccionar carreras
              </Button>
            }
          >
            Ya puedes elegir las carreras a las que quieres optar.
          </Alert>
        )}

        <div className={styles.dosColumnas}>
          <div className={styles.pila}>
            <DatosAcademicos perfil={perfil} onGuardado={setActualizado} />
            <FotoPerfil bloqueado={!editable(perfil, 'foto')} observada={estaObservado(perfil, 'foto')} onGuardada={recargar} />
          </div>
          <Requisitos perfil={perfil} />
        </div>

        <Card>
          <CardHeader title="Documentos" />
          <CardBody>
            <p className={styles.ayuda}>
              PDF, JPG o PNG, máximo {formatearTamano(perfil.limites.archivo_maximo)} por archivo. Si sustituyes un documento, la versión
              anterior se conserva como historial. Usas {formatearTamano(usada)} de {formatearTamano(maxima)}.
            </p>
            <ul className={styles.documentos}>
              {perfil.documentos.map(({ tipo, documento }) => (
                <Documento
                  key={tipo.id}
                  tipo={tipo}
                  documento={documento}
                  bloqueado={!editable(perfil, 'documento', tipo.id)}
                  observado={estaObservado(perfil, 'documento', tipo.id)}
                  onSubido={setActualizado}
                />
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
    </>
  )
}

function estaObservado(perfil, objetivo, tipoDocumento = null) {
  return perfil.a_corregir.some((a) => a.objetivo === objetivo && (a.tipo_documento ?? null) === tipoDocumento)
}

function Requisitos({ perfil }) {
  const cumplidos = perfil.requisitos.filter((r) => r.cumple).length
  return (
    <Card>
      <CardHeader title={`Requisitos (${cumplidos} de ${perfil.requisitos.length})`} />
      <CardBody>
        <ul className={styles.requisitos}>
          {perfil.requisitos.map((r) => (
            <li key={r.clave} className={r.cumple ? styles.cumple : undefined}>
              {r.cumple ? <CheckCircle2 aria-hidden="true" /> : <Circle aria-hidden="true" />}
              <span>
                {r.nombre}
                <span className={styles.srOnly}>{r.cumple ? ': cumplido' : ': pendiente'}</span>
              </span>
            </li>
          ))}
        </ul>
        {perfil.perfil_completo && <Badge tone="success">Perfil completo</Badge>}
      </CardBody>
    </Card>
  )
}

function DatosAcademicos({ perfil, onGuardado }) {
  const toast = useToast()
  const formulario = useFormulario({ centro_trabajo: perfil.centro_trabajo, indice_declarado: perfil.indice_declarado ?? '' })
  const editarCentro = editable(perfil, 'centro_trabajo')
  const editarIndice = editable(perfil, 'indice')

  function validar({ centro_trabajo, indice_declarado }) {
    const errores = {}
    if (!centro_trabajo.trim()) errores.centro_trabajo = 'Indica tu centro de trabajo actual.'
    const indice = Number(indice_declarado)
    if (indice_declarado === '' || Number.isNaN(indice) || indice < 0 || indice > 100) {
      errores.indice_declarado = 'Escribe un número entre 0 y 100.'
    }
    return errores
  }

  async function guardar(evento) {
    evento.preventDefault()
    const datos = await formulario.enviar(
      ({ centro_trabajo, indice_declarado }) => perfilAspirante.actualizar({ centro_trabajo, indice_declarado: Number(indice_declarado) }),
      validar,
    )
    if (datos) {
      onGuardado(datos)
      toast.exito('Tus datos se guardaron.')
    }
  }

  return (
    <Card>
      <CardHeader title="Datos académicos y laborales" />
      <CardBody>
        <form className={styles.formulario} onSubmit={guardar} noValidate>
          {formulario.errorGeneral && <Alert tone="danger">{formulario.errorGeneral}</Alert>}
          <Input
            label="Centro de trabajo actual"
            required
            maxLength={200}
            disabled={!editarCentro}
            hint={estaObservado(perfil, 'centro_trabajo') ? 'Observado: corrígelo.' : undefined}
            {...formulario.campo('centro_trabajo')}
          />
          <Input
            label="Índice académico de 12.º grado"
            required
            type="number"
            inputMode="decimal"
            min={0}
            max={100}
            step={0.01}
            hint={
              estaObservado(perfil, 'indice')
                ? 'Observado: corrígelo según tu certificación.'
                : 'De 0 a 100, como aparece en tu certificación. La entidad lo validará después.'
            }
            disabled={!editarIndice}
            {...formulario.campo('indice_declarado')}
          />
          {perfil.indice_validado != null && <p className={styles.ayuda}>Índice validado por la entidad: {perfil.indice_validado}</p>}
          {(editarCentro || editarIndice) && (
            <Button type="submit" icon={Save} loading={formulario.enviando}>
              Guardar datos
            </Button>
          )}
        </form>
      </CardBody>
    </Card>
  )
}

function FotoPerfil({ bloqueado, observada, onGuardada }) {
  const { usuario, actualizarUsuario } = useAuth()
  const toast = useToast()
  const actual = useArchivoPrivado(usuario.foto)
  const [nueva, setNueva] = useState(null)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  async function guardar() {
    setGuardando(true)
    setError('')
    try {
      actualizarUsuario(await actualizarPerfil({ foto: nueva }))
      setNueva(null)
      toast.exito('Tu foto se guardó.')
      onGuardada()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Foto de perfil" />
      <CardBody>
        <div className={styles.formulario}>
          <ImageInput
            label="Foto"
            hint={observada ? 'Observada: sube una nueva. JPG o PNG, máximo 5 MB.' : 'JPG o PNG, máximo 5 MB. Una foto de frente, tipo carné.'}
            accept="image/jpeg,image/png"
            value={nueva ?? actual ?? ''}
            onChange={(valor) => setNueva(valor instanceof File ? valor : null)}
            error={error}
            disabled={bloqueado}
          />
          {nueva && (
            <Button icon={Save} loading={guardando} onClick={guardar}>
              Guardar foto
            </Button>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

const MAX_MB = 5

function Documento({ tipo, documento, bloqueado, observado, onSubido }) {
  const toast = useToast()
  const entrada = useRef(null)
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState('')

  async function subir(evento) {
    const archivo = evento.target.files?.[0]
    evento.target.value = ''
    if (!archivo) return
    if (archivo.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo no puede superar ${MAX_MB} MB.`)
      return
    }
    setSubiendo(true)
    setError('')
    try {
      onSubido(await perfilAspirante.subirDocumento(tipo.id, archivo))
      toast.exito(`${tipo.nombre}: se guardó el archivo.`)
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setSubiendo(false)
    }
  }

  async function ver() {
    // La pestaña se abre antes de la descarga para que el navegador no la bloquee.
    const pestana = window.open('', '_blank')
    try {
      const url = URL.createObjectURL(await obtenerArchivo(documento.archivo))
      if (pestana) pestana.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (e) {
      pestana?.close()
      toast.error(mensajeDeError(e))
    }
  }

  return (
    <li className={styles.documento}>
      <div className={styles.documentoInfo}>
        <strong>{tipo.nombre}</strong>
        {tipo.obligatorio ? <Badge tone="info">Obligatorio</Badge> : <Badge>Opcional</Badge>}
        {observado && <Badge tone="danger">Observado</Badge>}
        <span className={styles.documentoEstado}>
          {documento
            ? `${documento.nombre_original} · ${formatearTamano(documento.tamano)} · ${formatearFechaHora(documento.subido_at)}`
            : 'Sin subir'}
        </span>
        {error && (
          <span className={styles.error} role="alert">
            {error}
          </span>
        )}
      </div>
      <div className={styles.documentoAcciones}>
        {documento && (
          <Button variant="ghost" size="sm" icon={Eye} onClick={ver} aria-label={`Ver ${tipo.nombre}`}>
            Ver
          </Button>
        )}
        {!bloqueado && (
          <>
            <input
              ref={entrada}
              type="file"
              accept={FORMATOS_DOCUMENTO}
              className={styles.srOnly}
              tabIndex={-1}
              aria-hidden="true"
              onChange={subir}
            />
            <Button
              variant={documento ? 'secondary' : 'primary'}
              size="sm"
              icon={Upload}
              loading={subiendo}
              onClick={() => entrada.current?.click()}
              aria-label={`${documento ? 'Sustituir' : 'Subir'} ${tipo.nombre}`}
            >
              {documento ? 'Sustituir' : 'Subir'}
            </Button>
          </>
        )}
      </div>
    </li>
  )
}
