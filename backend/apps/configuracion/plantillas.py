"""Sustitución de variables en las plantillas de correo.

Solo se admite `{{ variable }}`. No se usa el motor de plantillas de Django a
propósito: permitiría a quien edita la plantilla usar etiquetas como
`{% include %}` o `{% load %}`.
"""

import re

PATRON = re.compile(r"{{\s*(\w+)\s*}}")


def variables_usadas(texto):
    return set(PATRON.findall(texto))


def variables_desconocidas(texto, permitidas):
    return sorted(variables_usadas(texto) - set(permitidas))


def renderizar(texto, contexto):
    """Reemplaza cada `{{ variable }}` por su valor. Una variable sin valor queda vacía."""
    return PATRON.sub(lambda m: str(contexto.get(m.group(1), "")), texto)
