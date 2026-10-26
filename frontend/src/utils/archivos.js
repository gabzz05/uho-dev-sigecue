/** 1536 → "1,5 KB"; 5242880 → "5 MB". */
export function formatearTamano(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  const [valor, unidad] = bytes < 1024 * 1024 ? [bytes / 1024, 'KB'] : [bytes / (1024 * 1024), 'MB']
  return `${valor.toLocaleString('es-CU', { maximumFractionDigits: 1 })} ${unidad}`
}

export const FORMATOS_DOCUMENTO = 'application/pdf,image/jpeg,image/png'
