import { api } from './api'

/** Vista ejecutiva del panel: secciones por módulo y alertas operativas (RF-030). */
export const obtenerDashboard = () => api.get('/admin/dashboard/').then((r) => r.data)
