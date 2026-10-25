"""Carga los permisos del catálogo y los 13 roles de la ERS (sección 2.3).

La matriz de permisos es el punto de partida; el Superadmin la ajusta
desde el panel. Superadmin no necesita permisos: tiene acceso total.
Los datos están congelados aquí a propósito: cambios posteriores del
catálogo se hacen con migraciones nuevas.
"""

from django.db import migrations

MODULOS = {
    "dashboard": ["ver"],
    "nomencladores": ["ver", "crear", "editar", "eliminar"],
    "usuarios": ["ver", "crear", "editar", "eliminar"],
    "roles": ["ver", "crear", "editar", "eliminar"],
    "configuracion": ["ver", "editar"],
    "interes": ["ver", "crear", "editar", "eliminar", "exportar"],
    "plan_plazas": ["ver", "crear", "editar", "eliminar", "exportar"],
    "convocatorias": ["ver", "crear", "editar", "eliminar"],
    "solicitudes": ["ver", "editar", "exportar"],
    "otorgamiento": ["ver", "editar", "exportar"],
    "prematricula": ["ver", "editar", "exportar"],
    "notificaciones": ["ver", "crear"],
    "logs": ["ver"],
}

# Visibilidad de todos los procesos. Administración del sistema y logs quedan
# fuera: según la sección 9.1 los logs son solo para Superadmin y Jefe CI.
TODO_VER_EXPORTAR = [
    f"{m}.{a}" for m, acciones in MODULOS.items() for a in acciones if a in ("ver", "exportar")
    if m not in ("roles", "configuracion", "usuarios", "logs")
]

ADMIN_LOCAL = [
    "dashboard.ver",
    "nomencladores.ver", "nomencladores.crear", "nomencladores.editar",
    "usuarios.ver", "usuarios.crear", "usuarios.editar", "usuarios.eliminar",
    "interes.ver", "interes.crear", "interes.editar", "interes.exportar",
    "plan_plazas.ver", "plan_plazas.editar", "plan_plazas.exportar",
    "solicitudes.ver", "solicitudes.editar", "solicitudes.exportar",
    "otorgamiento.ver", "otorgamiento.exportar",
    "prematricula.ver", "prematricula.editar", "prematricula.exportar",
    "notificaciones.ver", "notificaciones.crear",
]
APROBADOR_LOCAL = [
    "dashboard.ver",
    "interes.ver", "interes.exportar",
    "plan_plazas.ver", "plan_plazas.editar", "plan_plazas.exportar",
    "solicitudes.ver", "solicitudes.exportar",
    "otorgamiento.ver", "otorgamiento.exportar",
    "prematricula.ver", "prematricula.exportar",
    "notificaciones.ver",
]
SECRETARIO_LOCAL = [
    "dashboard.ver",
    "interes.ver", "interes.crear", "interes.editar", "interes.exportar",
    "solicitudes.ver", "solicitudes.editar", "solicitudes.exportar",
    "otorgamiento.ver", "otorgamiento.exportar",
    "prematricula.ver", "prematricula.editar", "prematricula.exportar",
    "notificaciones.ver",
]
JEFE_AREA_LOCAL = [
    "dashboard.ver",
    "interes.ver",
    "plan_plazas.ver", "plan_plazas.editar",
    "solicitudes.ver",
    "notificaciones.ver",
]

ROLES = [
    # (codigo, nombre, ambito, descripcion, permisos)
    ("superadmin", "Superadmin", "global",
     "Control total del sistema: configuración, nomencladores, SMTP, parámetros y campos de prematrícula.", []),
    ("jefe_ci", "Jefe Comisión de Ingreso", "global",
     "Define la oferta, gestiona el plan de plazas, supervisa el proceso de ingreso y aprueba otorgamientos.",
     TODO_VER_EXPORTAR + [
         "nomencladores.crear", "nomencladores.editar",
         "interes.crear", "interes.editar", "interes.eliminar",
         "plan_plazas.crear", "plan_plazas.editar", "plan_plazas.eliminar",
         "convocatorias.crear", "convocatorias.editar", "convocatorias.eliminar",
         "solicitudes.editar", "otorgamiento.editar",
         "notificaciones.crear", "logs.ver",
     ]),
    ("secretaria_general", "Secretario(a) General", "global",
     "Visibilidad completa. Gestiona convocatorias y exporta reportes globales.",
     TODO_VER_EXPORTAR + ["convocatorias.crear", "convocatorias.editar", "notificaciones.crear"]),
    ("vicerrector", "Vicerrector de Formación", "global",
     "Aprueba las decisiones finales del Jefe de la Comisión de Ingreso. Visibilidad completa.",
     TODO_VER_EXPORTAR + ["otorgamiento.editar"]),
    ("admin_facultad", "Admin Facultad", "facultad",
     "Administra los datos de su facultad: carreras, usuarios locales, plan de plazas, solicitudes.", ADMIN_LOCAL),
    ("vicedecano", "Vicedecano Facultad", "facultad",
     "Revisa y aprueba planes de plazas de su facultad.", APROBADOR_LOCAL),
    ("secretario_facultad", "Secretario(a) Facultad", "facultad",
     "Gestión operativa: carga datos, revisa solicitudes y gestiona la prematrícula de su facultad.", SECRETARIO_LOCAL),
    ("jefe_area_facultad", "Jefe de Área Facultad", "facultad",
     "Consulta estadísticas y propone ajustes al plan de plazas de su área.", JEFE_AREA_LOCAL),
    ("admin_cum", "Admin CUM/FUM", "cum_fum",
     "Igual que Admin Facultad, en el ámbito de su CUM/FUM.", ADMIN_LOCAL),
    ("director_cum", "Director(a) CUM/FUM", "cum_fum",
     "Equivalente a Vicedecano en el CUM/FUM.", APROBADOR_LOCAL),
    ("secretario_cum", "Secretario(a) CUM/FUM", "cum_fum",
     "Equivalente a Secretario Facultad en el CUM/FUM.", SECRETARIO_LOCAL),
    ("jefe_area_cum", "Jefe de Área CUM/FUM", "cum_fum",
     "Equivalente a Jefe de Área Facultad en el CUM/FUM.", JEFE_AREA_LOCAL),
    ("aspirante", "Aspirante", "propio",
     "Ciudadano registrado que solicita carrera. Solo ve y gestiona su propia información.", []),
]


def cargar(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    Rol = apps.get_model("roles", "Rol")

    permisos = {}
    for modulo, acciones in MODULOS.items():
        for accion in acciones:
            permiso, _ = Permiso.objects.get_or_create(modulo=modulo, accion=accion)
            permisos[f"{modulo}.{accion}"] = permiso

    for codigo, nombre, ambito, descripcion, codigos in ROLES:
        rol, _ = Rol.objects.update_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "ambito": ambito, "descripcion": descripcion, "es_sistema": True},
        )
        rol.permisos.set([permisos[c] for c in set(codigos)])


def descargar(apps, schema_editor):
    apps.get_model("roles", "Rol").objects.filter(es_sistema=True).delete()
    apps.get_model("roles", "Permiso").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("roles", "0001_initial")]

    operations = [migrations.RunPython(cargar, descargar)]
