"""Plantillas de correo del sistema (RF-011) y las variables que admite cada una.

Cada feature que envía un correo agrega aquí su plantilla (variables y texto
por defecto) y una migración de datos que cree la fila. El texto lo edita el
Superadmin; las variables las fija el código. El texto por defecto se usa al
"restablecer" una plantilla.
"""

PLANTILLAS = {
    "activacion_cuenta": {
        "nombre": "Activación de cuenta",
        "descripcion": "Se envía al registrarse un aspirante (RF-045).",
        "variables": {
            "nombre": "Nombre del aspirante",
            "enlace": "Enlace para activar la cuenta",
            "horas": "Horas de validez del enlace",
        },
        "asunto": "SIGECUE — Activa tu cuenta",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "Gracias por registrarte en SIGECUE, el sistema de ingreso a las carreras por encuentro "
            "de la Universidad de Holguín.\n\n"
            "Para activar tu cuenta abre este enlace:\n\n"
            "{{ enlace }}\n\n"
            "El enlace es válido durante {{ horas }} horas. Si no activas la cuenta en ese plazo se "
            "eliminará y tendrás que registrarte de nuevo.\n\n"
            "Si no fuiste tú quien se registró, ignora este mensaje.\n\n"
            "Universidad de Holguín"
        ),
    },
}

