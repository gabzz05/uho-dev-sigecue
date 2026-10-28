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
    "recuperar_password": {
        "nombre": "Recuperación de contraseña",
        "descripcion": "Se envía al pedir restablecer la contraseña desde el inicio de sesión.",
        "variables": {
            "nombre": "Nombre del usuario",
            "enlace": "Enlace para elegir la contraseña nueva",
            "horas": "Horas de validez del enlace",
        },
        "asunto": "SIGECUE — Restablece tu contraseña",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "Recibimos una solicitud para restablecer la contraseña de tu cuenta en SIGECUE.\n\n"
            "Para elegir una contraseña nueva abre este enlace:\n\n"
            "{{ enlace }}\n\n"
            "El enlace es válido durante {{ horas }} horas y solo se puede usar una vez.\n\n"
            "Si no fuiste tú quien lo pidió, ignora este mensaje: tu contraseña no cambia.\n\n"
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
    "convocatoria_solicitud_abierta": {
        "nombre": "Convocatoria de solicitud abierta",
        "descripcion": "A quienes expresaron interés ese año, al abrir la primera convocatoria de solicitud (RF-041).",
        "variables": {
            "nombre": "Nombre del destinatario",
            "anio": "Año académico",
            "fecha_cierre": "Fecha de cierre de la convocatoria",
            "enlace": "Enlace para registrarse y solicitar",
        },
        "asunto": "SIGECUE — Abrió la convocatoria de matrícula {{ anio }}",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "Ya está abierta la convocatoria de solicitud de matrícula en las carreras por encuentro para el curso {{ anio }}. "
            "Puedes presentar tu solicitud hasta el {{ fecha_cierre }}.\n\n"
            "Regístrate o inicia sesión en:\n\n"
            "{{ enlace }}\n\n"
            "Universidad de Holguín"
        ),
    },
    "solicitud_confirmada": {
        "nombre": "Solicitud de matrícula confirmada",
        "descripcion": "Al aspirante cuando confirma su solicitud, con el resumen de carreras (paso 16 de 7.2). Solo la primera vez.",
        "variables": {
            "nombre": "Nombre del aspirante",
            "anio": "Año académico",
            "convocatoria": "Número de convocatoria (1.ª, 2.ª...)",
            "fecha_cierre": "Fecha de cierre de la convocatoria",
            "carreras": "Carreras elegidas, una por línea, en orden de prioridad",
        },
        "asunto": "SIGECUE — Recibimos tu solicitud de matrícula {{ anio }}",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "Recibimos tu solicitud de matrícula en la {{ convocatoria }} convocatoria del curso {{ anio }}, "
            "con estas carreras en orden de prioridad:\n\n"
            "{{ carreras }}\n\n"
            "Puedes modificarla en SIGECUE hasta el {{ fecha_cierre }}. Al cierre se congela la última versión.\n\n"
            "Universidad de Holguín"
        ),
    },
    "solicitud_observada": {
        "nombre": "Observación en la solicitud",
        "descripcion": "Al aspirante cuando una entidad observa un elemento de su solicitud o reabre una observación (RF-055).",
        "variables": {
            "nombre": "Nombre del aspirante",
            "anio": "Año académico",
            "elemento": "Elemento observado (documento, índice, centro de trabajo o foto)",
            "observacion": "Texto de la observación o motivo de la reapertura",
        },
        "asunto": 'SIGECUE — Hay una observación en tu solicitud de matrícula',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'Al revisar tu solicitud de matrícula del curso {{ anio }} se hizo una observación sobre: {{ elemento }}.\n'
            '\n'
            '{{ observacion }}\n'
            '\n'
            'Entra en SIGECUE, corrígelo en tu perfil y pulsa «Enviar corrección». Mientras la observación no se resuelva, tu solicitud no participa en el otorgamiento de plazas.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "observacion_corregida": {
        "nombre": "Observación corregida por el aspirante",
        "descripcion": "A quien hizo la observación cuando el aspirante envía la corrección (solo en la aplicación).",
        "variables": {
            "nombre": "Nombre del destinatario",
            "aspirante": "Nombre del aspirante",
            "elementos": "Elementos corregidos",
        },
        "asunto": 'SIGECUE — {{ aspirante }} corrigió lo observado',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            '{{ aspirante }} envió la corrección de: {{ elementos }}.\n'
            '\n'
            'Revísala en SIGECUE y resuelve o reabre la observación.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "plaza_otorgada": {
        "nombre": 'Plaza otorgada',
        "descripcion": 'Al aspirante que obtuvo plaza, al publicarse el otorgamiento (RF-060).',
        "variables": {
            "nombre": "Nombre del aspirante",
            "anio": "Año académico",
            "carrera": "Carrera otorgada",
            "entidad": "Facultad o CUM/FUM",
        },
        "asunto": 'SIGECUE — Obtuviste plaza en {{ carrera }}',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            '¡Felicidades! Obtuviste plaza en la carrera {{ carrera }} ({{ entidad }}) para el curso {{ anio }}.\n'
            '\n'
            'Próximos pasos: entra en SIGECUE y completa la prematrícula, donde se te pedirán los documentos que faltan. Te avisaremos cuando esté disponible y de los plazos para presentarla.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "no_seleccionado_segunda": {
        "nombre": 'No seleccionado (habrá segunda convocatoria)',
        "descripcion": 'A quienes no obtuvieron plaza, si el Vicerrector indicó que habrá segunda convocatoria (RF-061).',
        "variables": {
            "nombre": "Nombre del aspirante",
            "anio": "Año académico",
        },
        "asunto": 'SIGECUE — Resultado de tu solicitud de matrícula {{ anio }}',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'No obtuviste plaza en esta convocatoria del curso {{ anio }}.\n'
            '\n'
            'Podrás participar en la segunda convocatoria con las plazas restantes. Te avisaremos cuando se abra.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "no_seleccionado_final": {
        "nombre": 'No seleccionado (sin segunda convocatoria)',
        "descripcion": 'A quienes no obtuvieron plaza, si no habrá segunda convocatoria (RF-061).',
        "variables": {
            "nombre": "Nombre del aspirante",
            "anio": "Año académico",
        },
        "asunto": 'SIGECUE — Resultado de tu solicitud de matrícula {{ anio }}',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'No obtuviste plaza en el curso {{ anio }}. El proceso concluyó para esta convocatoria.\n'
            '\n'
            'Gracias por tu interés en las carreras por encuentro de la Universidad de Holguín.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "otorgamiento_para_aprobacion": {
        "nombre": 'Otorgamiento pendiente de aprobación',
        "descripcion": 'Al Vicerrector cuando el Jefe CI aprueba el otorgamiento.',
        "variables": {
            "nombre": "Nombre del destinatario",
            "anio": "Año académico",
            "convocatoria": "Número de convocatoria",
        },
        "asunto": 'SIGECUE — Otorgamiento {{ anio }} pendiente de aprobación',
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'El Jefe de la Comisión de Ingreso aprobó el otorgamiento de la {{ convocatoria }} convocatoria del curso {{ anio }}. Revísalo en SIGECUE: al aprobarlo se publica y se avisa a los aspirantes.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "prematricula_abierta": {
        "nombre": "Prematrícula abierta",
        "descripcion": "A cada otorgado cuando se abre su período de prematrícula (RF-065).",
        "variables": {
            "nombre": "Nombre del aspirante",
            "carrera": "Carrera otorgada",
            "entidad": "Facultad o CUM/FUM",
            "fecha_cierre": "Fecha de cierre",
        },
        "asunto": "SIGECUE — Ya puedes hacer tu prematrícula en {{ carrera }}",
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'Ya está abierta la prematrícula de {{ carrera }} ({{ entidad }}). Entra en SIGECUE y completa el formulario: puedes guardarlo y terminarlo en varias sesiones hasta el {{ fecha_cierre }}.\n'
            '\n'
            'Tu carnet de identidad y tu certificación de estudios ya están en tu perfil: no tienes que volver a subirlos.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "prematricula_recordatorio": {
        "nombre": "Recordatorio de prematrícula",
        "descripcion": "A quien no completó la prematrícula, a 5 días y a 1 día del cierre (RF-070).",
        "variables": {
            "nombre": "Nombre del aspirante",
            "carrera": "Carrera otorgada",
            "entidad": "Facultad o CUM/FUM",
            "fecha_cierre": "Fecha de cierre",
            "dias": "Días que faltan",
        },
        "asunto": "SIGECUE — Faltan {{ dias }} día(s) para cerrar tu prematrícula",
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'Tu prematrícula de {{ carrera }} ({{ entidad }}) todavía no está completa. El plazo cierra el {{ fecha_cierre }}.\n'
            '\n'
            'Entra en SIGECUE, entrega lo que falta y envíala.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "prematricula_correccion": {
        "nombre": "Correcciones en la prematrícula",
        "descripcion": "Al aspirante cuando la entidad pide corregir documentos o campos (RF-069). No pierde la plaza.",
        "variables": {
            "nombre": "Nombre del aspirante",
            "carrera": "Carrera otorgada",
            "entidad": "Facultad o CUM/FUM",
            "fecha_cierre": "Fecha de cierre",
            "correcciones": "Lista de lo que hay que corregir",
        },
        "asunto": "SIGECUE — Hay correcciones en tu prematrícula",
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'Al revisar tu prematrícula de {{ carrera }} ({{ entidad }}) hace falta corregir:\n'
            '\n'
            '{{ correcciones }}\n'
            '\n'
            'Corrígelo en SIGECUE y vuelve a enviarla. No pierdes tu plaza.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
    "prematricula_aprobada": {
        "nombre": "Prematrícula aprobada",
        "descripcion": "Al aspirante cuando la entidad aprueba su prematrícula.",
        "variables": {
            "nombre": "Nombre del aspirante",
            "carrera": "Carrera otorgada",
            "entidad": "Facultad o CUM/FUM",
            "fecha_cierre": "Fecha de cierre",
        },
        "asunto": "SIGECUE — Tu prematrícula fue aprobada",
        "cuerpo": (
            'Hola, {{ nombre }}:\n'
            '\n'
            'Tu prematrícula de {{ carrera }} ({{ entidad }}) fue aprobada. La entidad te informará los próximos pasos.\n'
            '\n'
            'Universidad de Holguín'
        ),
    },
}
