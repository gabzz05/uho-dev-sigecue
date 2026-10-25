import {
  Building2,
  ClipboardList,
  FileStack,
  FolderOpen,
  GraduationCap,
  LayoutDashboard,
  Lightbulb,
  ListTree,
  Megaphone,
  ScrollText,
  Settings,
  ShieldCheck,
  Trophy,
  Users,
} from 'lucide-react'

/**
 * Menú del panel administrativo. Cada entrada se muestra solo si el usuario
 * tiene su permiso; las rutas se generan a partir de esta misma lista.
 */
export const MENU_ADMIN = [
  {
    titulo: 'Principal',
    items: [
      { path: '', label: 'Dashboard', icon: LayoutDashboard, permiso: 'dashboard.ver' },
      { path: 'convocatorias', label: 'Convocatorias', icon: Megaphone, permiso: 'convocatorias.ver' },
      { path: 'interes', label: 'Interés de la población', icon: Lightbulb, permiso: 'interes.ver' },
    ],
  },
  {
    titulo: 'Proceso',
    items: [
      { path: 'plan-plazas', label: 'Plan de Plazas', icon: ClipboardList, permiso: 'plan_plazas.ver' },
      { path: 'solicitudes', label: 'Solicitudes', icon: FolderOpen, permiso: 'solicitudes.ver' },
      { path: 'otorgamiento', label: 'Otorgamiento', icon: Trophy, permiso: 'otorgamiento.ver' },
      { path: 'prematricula', label: 'Prematrícula', icon: FileStack, permiso: 'prematricula.ver' },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { path: 'carreras', label: 'Carreras', icon: GraduationCap, permiso: 'nomencladores.ver' },
      { path: 'entidades', label: 'Facultades / CUM', icon: Building2, permiso: 'nomencladores.ver' },
      { path: 'nomencladores', label: 'Otros nomencladores', icon: ListTree, permiso: 'nomencladores.ver' },
      { path: 'usuarios', label: 'Usuarios', icon: Users, permiso: 'usuarios.ver' },
      { path: 'roles', label: 'Roles y permisos', icon: ShieldCheck, permiso: 'roles.ver' },
      { path: 'configuracion', label: 'Configuración', icon: Settings, permiso: 'configuracion.ver' },
      { path: 'logs', label: 'Logs de auditoría', icon: ScrollText, permiso: 'logs.ver' },
    ],
  },
]

/** Secciones del menú con solo las entradas permitidas; las secciones vacías se omiten. */
export function menuVisible(tienePermiso) {
  return MENU_ADMIN.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => tienePermiso(item.permiso)),
  })).filter((seccion) => seccion.items.length > 0)
}
