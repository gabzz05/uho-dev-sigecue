"""Reparto de plazas (sección 5.9, con las decisiones del cliente).

- Una sola plaza por aspirante: la de mayor prioridad (según su propio orden)
  que todavía tenga plaza libre.
- Se recorre a los aspirantes en orden de ranking: índice validado de mayor a
  menor, luego `confirmada_at` y, como último desempate técnico, el id.
- Se descarta la regla 5 de la ERS (CUM antes que Facultad): manda la prioridad
  elegida por el aspirante.
- Los ajustes manuales vigentes se aplican primero: `fijados` ocupa la plaza
  indicada y `prohibidos` excluye opciones concretas. Después el recorrido normal
  cubre las vacantes, lo que resuelve las cascadas.

Es una función pura (sin base de datos) para poder probarla de forma aislada.
"""

from dataclasses import dataclass, field


@dataclass
class Candidato:
    clave: int
    # (clave_opcion, oferta_id) ordenadas por prioridad: la primera es la preferida.
    opciones: list = field(default_factory=list)


class PlazasInsuficientes(Exception):
    def __init__(self, oferta_id):
        super().__init__(oferta_id)
        self.oferta_id = oferta_id


def repartir(candidatos, capacidad, fijados=None, prohibidos=frozenset()):
    """Devuelve `{clave_candidato: clave_opcion | None}` y la capacidad sobrante.

    - `candidatos`: en orden de ranking.
    - `capacidad`: `{oferta_id: plazas}`; no se modifica.
    - `fijados`: `{clave_candidato: clave_opcion}` de los ajustes "otorgar".
    - `prohibidos`: `{(clave_candidato, clave_opcion)}` de los ajustes "quitar".

    Lanza `PlazasInsuficientes` si los fijados superan las plazas de una oferta.
    """
    fijados = fijados or {}
    libres = dict(capacidad)
    asignacion = {}
    oferta_de = {c.clave: dict(c.opciones) for c in candidatos}

    for clave, opcion in fijados.items():
        oferta = oferta_de[clave][opcion]
        if libres.get(oferta, 0) <= 0:
            raise PlazasInsuficientes(oferta)
        libres[oferta] -= 1
        asignacion[clave] = opcion

    for candidato in candidatos:
        if candidato.clave in asignacion:
            continue
        asignacion[candidato.clave] = None
        for opcion, oferta in candidato.opciones:
            if (candidato.clave, opcion) in prohibidos:
                continue
            if libres.get(oferta, 0) > 0:
                libres[oferta] -= 1
                asignacion[candidato.clave] = opcion
                break
    return asignacion, libres
