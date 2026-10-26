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
    "interes_confirmado": {
        "nombre": "Interés registrado",
        "descripcion": "Se envía al registrar una expresión de interés en la landing (RF-021).",
        "variables": {
            "nombre": "Nombre de quien expresó interés",
            "carrera": "Carrera",
            "entidad": "Facultad o CUM/FUM",
            "anio": "Año académico",
        },
        "asunto": "SIGECUE — Registramos tu interés en {{ carrera }}",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "Registramos tu interés en la carrera {{ carrera }} ({{ entidad }}) para el curso {{ anio }}.\n\n"
            "Te avisaremos a este correo cuando se abra la convocatoria oficial de solicitud de matrícula.\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_enviado": {
        "nombre": "Plan de plazas enviado a las entidades",
        "descripcion": "A quienes responden por cada entidad cuando la CI envía el plan (RF-033).",
        "variables": {"nombre": "Nombre del destinatario", "anio": "Año académico", "entidad": "Facultad o CUM/FUM"},
        "asunto": "SIGECUE — Plan de plazas {{ anio }} para revisión",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "La Comisión de Ingreso envió la propuesta del plan de plazas {{ anio }} para {{ entidad }}.\n\n"
            "Revísala en SIGECUE: puedes aceptarla, ajustar las cantidades, pedir quitar carreras o agregar otras, "
            "justificando cada cambio. Luego envía la propuesta de tu entidad.\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_para_aprobacion": {
        "nombre": "Plan de plazas pendiente de aprobación",
        "descripcion": "Al Vicerrector cuando la CI genera la versión final (RF-036).",
        "variables": {"nombre": "Nombre del destinatario", "anio": "Año académico", "version": "Número de versión"},
        "asunto": "SIGECUE — Plan de plazas {{ anio }} pendiente de aprobación",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "La Comisión de Ingreso generó la versión {{ version }} del plan de plazas {{ anio }} y está pendiente de tu aprobación.\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_devuelto": {
        "nombre": "Plan de plazas devuelto",
        "descripcion": "A la Comisión de Ingreso cuando el Vicerrector devuelve el plan (paso 26 de 7.3).",
        "variables": {"nombre": "Nombre del destinatario", "anio": "Año académico", "observaciones": "Observaciones del Vicerrector"},
        "asunto": "SIGECUE — Plan de plazas {{ anio }} devuelto con observaciones",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "El Vicerrector devolvió el plan de plazas {{ anio }} con estas observaciones:\n\n"
            "{{ observaciones }}\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_publicado": {
        "nombre": "Plan de plazas publicado",
        "descripcion": "A los usuarios internos cuando el Vicerrector aprueba y publica el plan (paso 27 de 7.3).",
        "variables": {"nombre": "Nombre del destinatario", "anio": "Año académico"},
        "asunto": "SIGECUE — Plan de plazas {{ anio }} aprobado y publicado",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "El Vicerrector de Formación aprobó el plan de plazas {{ anio }}. Ya puedes consultarlo en SIGECUE.\n\n"
            "Universidad de Holguín"
        ),
    },
}
