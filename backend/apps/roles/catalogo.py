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
# Descargar los documentos personales de los aspirantes (CI, certificación, foto).
DESCARGAR_DOCUMENTOS = "documentos_descargar"
# Etapas del otorgamiento: lo genera la Secretaría General, lo revisa y aprueba
# el Jefe CI, y lo revisa, aprueba y publica el Vicerrector.
GENERAR = "generar"
APROBAR = "aprobar"
PUBLICAR = "publicar"
# Fijar el período de prematrícula (Secretaría General).
CONFIGURAR = "configurar"

ACCIONES = {
    VER: "Ver",
    CREAR: "Crear",
    EDITAR: "Editar",
    ELIMINAR: "Eliminar",
    EXPORTAR: "Exportar",
    DESCARGAR_DOCUMENTOS: "Descargar documentos",
    GENERAR: "Generar",
    APROBAR: "Aprobar",
    PUBLICAR: "Publicar",
    CONFIGURAR: "Configurar período",
}

CRUD = [VER, CREAR, EDITAR, ELIMINAR]

MODULOS = {
    "dashboard": ("Dashboard", [VER]),
    "nomencladores": ("Nomencladores", CRUD),
    # Los usuarios no se borran: se desactivan (permiso editar).
    "usuarios": ("Usuarios", [VER, CREAR, EDITAR]),
    "roles": ("Roles y permisos", CRUD),
    "configuracion": ("Configuración", [VER, EDITAR]),
    "interes": ("Convocatoria de interés", CRUD + [EXPORTAR]),
    "plan_plazas": ("Plan de plazas", CRUD + [EXPORTAR]),
    "convocatorias": ("Convocatorias de solicitud", CRUD),
    "solicitudes": ("Solicitudes", [VER, EDITAR, EXPORTAR, DESCARGAR_DOCUMENTOS]),
    # Editar depende de la etapa: el Jefe CI (aprobar) o el Vicerrector (publicar).
    "otorgamiento": ("Otorgamiento", [VER, EXPORTAR, GENERAR, APROBAR, PUBLICAR]),
    "prematricula": ("Prematrícula", [VER, EDITAR, EXPORTAR, CONFIGURAR]),
    "notificaciones": ("Notificaciones", [VER, CREAR]),
    "logs": ("Logs de auditoría", [VER]),
}


def sincronizar_permisos(Permiso):
    """Crea los permisos del catálogo que no existan. Recibe el modelo (real o histórico)."""
    for modulo, (_, acciones) in MODULOS.items():
        for accion in acciones:
            Permiso.objects.get_or_create(modulo=modulo, accion=accion)
