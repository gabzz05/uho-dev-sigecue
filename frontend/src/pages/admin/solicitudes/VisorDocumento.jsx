import { Download } from 'lucide-react'
import { Button, Modal, Spinner } from '../../../components/ui'
import { useArchivoPrivado } from '../../../hooks/useArchivoPrivado'
import styles from './Solicitudes.module.css'

/**
 * Visor inline de un documento del aspirante (RF-054): PDF en un marco o imagen.
 * El archivo se pide con el token; cada apertura queda auditada en la API.
 */
export function VisorDocumento({ documento, titulo, onClose }) {
  const url = useArchivoPrivado(documento?.archivo)
  const esPdf = documento?.formato === 'PDF'

  return (
    <Modal
      open={Boolean(documento)}
      onClose={onClose}
      title={titulo}
      description={documento && `${documento.nombre_original} · versión ${documento.version}`}
      size="lg"
      footer={
        url && (
          <Button as="a" href={url} download={documento.nombre_original} variant="secondary" icon={Download}>
            Descargar
          </Button>
        )
      }
    >
      {!url ? (
        <Spinner label="Cargando el documento" />
      ) : esPdf ? (
        <iframe src={url} title={titulo} className={styles.visorPdf} />
      ) : (
        <img src={url} alt={titulo} className={styles.visorImagen} />
      )}
    </Modal>
  )
}
