"""Catálogo de permisos asignables (RE-006): módulo × acción.

Cuando un feature agrega un módulo nuevo, se añade aquí y se crea una
migración de datos que llame a `sincronizar_permisos` para dar de alta
las filas de `Permiso` que falten.
"""

VER = "ver"
CREAR = "crear"
EDITAR = "editar"
ELIMINAR = "eliminar"
EXPORTAR = "exportar"

ACCIONES = {
    VER: "Ver",
    CREAR: "Crear",
    EDITAR: "Editar",
    ELIMINAR: "Eliminar",
    EXPORTAR: "Exportar",
}

CRUD = [VER, CREAR, EDITAR, ELIMINAR]

MODULOS = {
    "dashboard": ("Dashboard", [VER]),
    "nomencladores": ("Nomencladores", CRUD),
    "usuarios": ("Usuarios", CRUD),
    "roles": ("Roles y permisos", CRUD),
    "configuracion": ("Configuración", [VER, EDITAR]),
    "interes": ("Convocatoria de interés", CRUD + [EXPORTAR]),
    "plan_plazas": ("Plan de plazas", CRUD + [EXPORTAR]),
    "convocatorias": ("Convocatorias de solicitud", CRUD),
    "solicitudes": ("Solicitudes", [VER, EDITAR, EXPORTAR]),
    "otorgamiento": ("Otorgamiento", [VER, EDITAR, EXPORTAR]),
    "prematricula": ("Prematrícula", [VER, EDITAR, EXPORTAR]),
    "notificaciones": ("Notificaciones", [VER, CREAR]),
    "logs": ("Logs de auditoría", [VER]),
}


def sincronizar_permisos(Permiso):
    """Crea los permisos del catálogo que no existan. Recibe el modelo (real o histórico)."""
    for modulo, (_, acciones) in MODULOS.items():
        for accion in acciones:
            Permiso.objects.get_or_create(modulo=modulo, accion=accion)
