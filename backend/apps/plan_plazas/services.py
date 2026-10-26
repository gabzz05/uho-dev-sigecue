"""Flujo del plan de plazas (sección 7.3). Cada cambio queda en el historial (RF-038)."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.ambito import es_de_su_entidad
from apps.core.exceptions import ErrorDeNegocio
from apps.nomencladores.models import CumFum, Facultad
from apps.notificaciones.services import notificar
from apps.oferta.models import OfertaCarrera
from apps.roles.models import Rol
from apps.users.models import Usuario

from .models import ComentarioPlan, HistorialPlan, LineaPlan, PlanEntidad, PlanPlazas

E = PlanPlazas.Estado
A = LineaPlan.AccionEntidad
D = LineaPlan.DecisionCI

# --- Quién puede qué ----------------------------------------------------------


def es_ci(usuario):
    """Comisión de Ingreso: rol global con permiso de editar el plan."""
    return usuario.es_global and usuario.tiene_permiso("plan_plazas", "editar")


def es_vicerrector(usuario):
    return usuario.es_superadmin or (usuario.rol_id is not None and usuario.rol.codigo == "vicerrector")


def responde_por_entidad(usuario):
    """Admin, Vicedecano o Director de la entidad. Los Jefes de Área solo comentan."""
    return (
        not usuario.es_global
        and usuario.entidad is not None
        and usuario.tiene_permiso("plan_plazas", "editar")
        and not (usuario.rol_id and usuario.rol.requiere_area)
    )


def _exigir(condicion, mensaje):
    if not condicion:
        raise ErrorDeNegocio(mensaje)


def _exigir_estado(plan, *estados):
    if plan.estado not in estados:
        nombres = ", ".join(E(e).label for e in estados)
        raise ErrorDeNegocio(f"Esta acción solo está disponible con el plan en estado: {nombres}.")


def _exigir_ci(usuario):
    _exigir(es_ci(usuario), "Esta acción corresponde a la Comisión de Ingreso.")


def _actual(plan_o_id):
    """Estado actual del plan desde la base de datos (las instancias en memoria pueden estar desactualizadas)."""
    return PlanPlazas.objects.get(pk=getattr(plan_o_id, "pk", plan_o_id))


def _bloquear(plan):
    """Relee el plan bloqueando su fila: dos transiciones simultáneas no se pisan
    y la instancia recibida puede estar desactualizada. Usar dentro de una transacción."""
    return PlanPlazas.objects.select_for_update().get(pk=plan.pk)


# --- Historial -------------------------------------------------------------------


def _registrar(plan, usuario, accion, linea=None, antes="", despues="", comentario=""):
    HistorialPlan.objects.create(
        plan=plan, version=plan.version, linea=linea, descripcion_linea=str(linea) if linea else "",
        accion=accion, valor_anterior="" if antes is None else str(antes), valor_nuevo="" if despues is None else str(despues),
        comentario=comentario, usuario=usuario, usuario_nombre=usuario.get_username(),
    )


def _texto_plazas(valor):
    return "Fuera del plan" if valor is None else str(valor)


# --- Destinatarios de las notificaciones ------------------------------------------


def _usuarios_con_permiso(modulo, accion):
    roles = Rol.objects.filter(activo=True, permisos__modulo=modulo, permisos__accion=accion)
    return Usuario.objects.filter(is_active=True).filter(rol__in=roles) | Usuario.objects.filter(is_active=True, is_superuser=True)


def _responsables_de(entidad_plan):
    filtro = {"facultad": entidad_plan.facultad} if entidad_plan.facultad_id else {"cum_fum": entidad_plan.cum_fum}
    return [u for u in _usuarios_con_permiso("plan_plazas", "editar").filter(**filtro).distinct() if responde_por_entidad(u)]


# --- Creación ----------------------------------------------------------------------


def crear_plan(anio_academico, actor, notas=""):
    _exigir_ci(actor)
    try:
        with transaction.atomic():
            plan = PlanPlazas.objects.create(anio_academico=anio_academico, notas=notas, created_by=actor)
    except IntegrityError:
        raise ErrorDeNegocio("Ya existe el plan de plazas de ese año. Para cambiarlo una vez publicado, crea una versión complementaria.")
    _registrar(plan, actor, "Creó el plan")
    return plan


def plan_vigente(anio_academico):
    """Último plan publicado del año (base o complementario)."""
    return PlanPlazas.objects.filter(anio_academico=anio_academico, estado=E.PUBLICADO).order_by("-fecha_aprobacion").first()


def complementaria_en_curso(plan):
    raiz = plan.complementaria_de or plan
    return PlanPlazas.objects.filter(complementaria_de=raiz).exclude(estado=E.PUBLICADO).exists()


def admite_complementaria(plan):
    """Solo sobre el plan vigente del año y sin otra versión complementaria en curso."""
    vigente = plan_vigente(plan.anio_academico)
    return vigente is not None and vigente.pk == plan.pk and not complementaria_en_curso(vigente)


@transaction.atomic
def crear_complementaria(base, actor, notas=""):
    """RF-039: un plan nuevo con su propio flujo que parte de los valores aprobados vigentes."""
    _exigir_ci(actor)
    base = _bloquear(base)
    _exigir(base.estado == E.PUBLICADO, "Solo se crea una versión complementaria de un plan publicado.")
    _exigir(not complementaria_en_curso(base), "Ya hay una versión complementaria en curso para este año.")
    _exigir(plan_vigente(base.anio_academico) == base, "Crea la versión complementaria a partir del plan vigente del año.")
    raiz = base.complementaria_de or base

    vigente = base
    plan = PlanPlazas.objects.create(anio_academico=base.anio_academico, complementaria_de=raiz, notas=notas, created_by=actor)
    for linea in vigente.lineas.exclude(plazas_aprobadas=None):
        LineaPlan.objects.create(
            plan=plan, carrera=linea.carrera, facultad=linea.facultad, cum_fum=linea.cum_fum, oferta=linea.oferta,
            plazas_propuestas=linea.plazas_aprobadas,
        )
    _registrar(plan, actor, "Creó la versión complementaria", comentario=f"A partir del plan vigente ({vigente})")
    return plan


# --- Borrador (CI) -------------------------------------------------------------------


def cargar_oferta(plan, actor):
    """Agrega una línea (0 plazas) por cada carrera ofertada ese año que aún no esté en el plan."""
    _exigir_ci(actor)
    plan = _actual(plan)
    _exigir_estado(plan, E.BORRADOR)
    existentes = {(l.carrera_id, l.facultad_id, l.cum_fum_id) for l in plan.lineas.all()}
    nuevas = [
        LineaPlan(plan=plan, carrera=o.carrera, facultad=o.facultad, cum_fum=o.cum_fum, oferta=o)
        for o in OfertaCarrera.objects.filter(anio_academico=plan.anio_academico, carrera__activo=True)
        if (o.carrera_id, o.facultad_id, o.cum_fum_id) not in existentes
    ]
    LineaPlan.objects.bulk_create(nuevas)
    if nuevas:
        _registrar(plan, actor, "Cargó la oferta del año", despues=f"{len(nuevas)} carreras")
    return len(nuevas)


def agregar_linea_ci(plan, carrera, facultad, cum_fum, plazas, actor):
    _exigir_ci(actor)
    plan = _actual(plan)
    _exigir_estado(plan, E.BORRADOR)
    _exigir((facultad is None) != (cum_fum is None), "Indica una Facultad o un CUM/FUM (solo uno).")
    try:
        with transaction.atomic():
            linea = LineaPlan.objects.create(plan=plan, carrera=carrera, facultad=facultad, cum_fum=cum_fum, plazas_propuestas=plazas)
    except IntegrityError:
        raise ErrorDeNegocio("Esa carrera ya está en el plan para esa entidad.")
    _registrar(plan, actor, "Agregó una carrera", linea, despues=plazas)
    return linea


def actualizar_linea_ci(linea, plazas, actor):
    _exigir_ci(actor)
    linea.plan = _actual(linea.plan_id)
    _exigir_estado(linea.plan, E.BORRADOR)
    anterior = linea.plazas_propuestas
    linea.plazas_propuestas = plazas
    linea.save(update_fields=["plazas_propuestas"])
    _registrar(linea.plan, actor, "Cambió la propuesta inicial", linea, anterior, plazas)
    return linea


def quitar_linea_ci(linea, actor):
    _exigir_ci(actor)
    linea.plan = _actual(linea.plan_id)
    _exigir_estado(linea.plan, E.BORRADOR)
    _registrar(linea.plan, actor, "Quitó una carrera del borrador", linea, linea.plazas_propuestas, None)
    linea.delete()


@transaction.atomic
def enviar(plan, actor):
    """RF-033: se envía a todas las Facultades y CUM/FUM activos."""
    _exigir_ci(actor)
    plan = _bloquear(plan)
    _exigir_estado(plan, E.BORRADOR)
    _exigir(plan.lineas.exists(), "Agrega al menos una carrera antes de enviar el plan.")

    entidades = [PlanEntidad(plan=plan, facultad=f) for f in Facultad.objects.filter(activo=True)]
    entidades += [PlanEntidad(plan=plan, cum_fum=c) for c in CumFum.objects.filter(activo=True)]
    PlanEntidad.objects.bulk_create(entidades)
    plan.estado = E.ENVIADO
    plan.save(update_fields=["estado"])
    _registrar(plan, actor, "Envió el plan a las entidades")

    for entidad_plan in plan.entidades.select_related("facultad", "cum_fum"):
        notificar(_responsables_de(entidad_plan), "plan_enviado", {"anio": plan.anio_academico, "entidad": str(entidad_plan.entidad)})
    return plan


# --- Revisión de las entidades (RF-034) -----------------------------------------------


def entidad_del_usuario(plan, usuario):
    filtro = {"facultad": usuario.facultad} if usuario.facultad_id else {"cum_fum": usuario.cum_fum}
    entidad_plan = plan.entidades.filter(**filtro).first()
    _exigir(entidad_plan is not None, "Tu entidad no participa en este plan.")
    return entidad_plan


def _exigir_revision_abierta(plan, actor):
    _exigir(responde_por_entidad(actor), "Solo el Admin, el Vicedecano o el Director de la entidad responden el plan.")
    plan = _actual(plan)
    _exigir_estado(plan, E.ENVIADO)
    entidad_plan = entidad_del_usuario(plan, actor)
    _exigir(entidad_plan.estado != PlanEntidad.Estado.PROPUESTA_ENVIADA, "Tu entidad ya envió su propuesta.")
    return entidad_plan


def _marcar_en_revision(entidad_plan):
    if entidad_plan.estado == PlanEntidad.Estado.PENDIENTE:
        entidad_plan.estado = PlanEntidad.Estado.EN_REVISION
        entidad_plan.save(update_fields=["estado"])


def responder_linea(linea, accion, plazas, comentario, actor):
    entidad_plan = _exigir_revision_abierta(linea.plan, actor)
    _exigir(es_de_su_entidad(actor, linea.facultad, linea.cum_fum), "Esa línea no es de tu entidad.")
    _exigir(linea.origen == LineaPlan.Origen.CI, "Para cambiar una carrera que solicitaste, retírala y vuelve a solicitarla.")
    _exigir(accion in (A.ACEPTAR, A.MODIFICAR, A.QUITAR), "Acción no válida.")
    comentario = (comentario or "").strip()
    if accion == A.MODIFICAR:
        _exigir(plazas is not None, "Indica la cantidad de plazas que propones.")
    if accion != A.ACEPTAR:
        _exigir(comentario, "Justifica el cambio con un comentario (RF-034).")

    antes = _texto_plazas(linea.propuesta_de_la_entidad())
    linea.accion_entidad = accion
    linea.plazas_entidad = plazas if accion == A.MODIFICAR else None
    linea.comentario_entidad = comentario if accion != A.ACEPTAR else ""
    linea.save(update_fields=["accion_entidad", "plazas_entidad", "comentario_entidad"])
    _marcar_en_revision(entidad_plan)
    _registrar(linea.plan, actor, f"La entidad: {A(accion).label.lower()}", linea, antes, _texto_plazas(linea.propuesta_de_la_entidad()), comentario)
    return linea


def solicitar_carrera(plan, carrera, plazas, comentario, actor):
    entidad_plan = _exigir_revision_abierta(plan, actor)
    comentario = (comentario or "").strip()
    _exigir(comentario, "Justifica la solicitud con un comentario (RF-034).")
    _exigir(carrera.activo, "La carrera está desactivada en el catálogo.")
    try:
        with transaction.atomic():
            linea = LineaPlan.objects.create(
                plan=plan, carrera=carrera, facultad=entidad_plan.facultad, cum_fum=entidad_plan.cum_fum,
                origen=LineaPlan.Origen.ENTIDAD, accion_entidad=A.AGREGAR, plazas_entidad=plazas, comentario_entidad=comentario,
            )
    except IntegrityError:
        raise ErrorDeNegocio("Esa carrera ya está en el plan de tu entidad.")
    _marcar_en_revision(entidad_plan)
    _registrar(plan, actor, "La entidad solicita agregar una carrera", linea, None, plazas, comentario)
    return linea


def retirar_solicitud(linea, actor):
    _exigir_revision_abierta(linea.plan, actor)
    _exigir(linea.origen == LineaPlan.Origen.ENTIDAD and es_de_su_entidad(actor, linea.facultad, linea.cum_fum),
            "Solo se retiran carreras que tu entidad solicitó agregar.")
    _registrar(linea.plan, actor, "La entidad retiró su solicitud", linea, linea.plazas_entidad, None)
    linea.delete()


def enviar_propuesta(plan, actor, comentario=""):
    entidad_plan = _exigir_revision_abierta(plan, actor)
    entidad_plan.estado = PlanEntidad.Estado.PROPUESTA_ENVIADA
    entidad_plan.comentario = (comentario or "").strip()
    entidad_plan.enviada_por = actor
    entidad_plan.enviada_at = timezone.now()
    entidad_plan.save(update_fields=["estado", "comentario", "enviada_por", "enviada_at"])
    _registrar(plan, actor, f"{entidad_plan.entidad} envió su propuesta", comentario=entidad_plan.comentario)
    return entidad_plan


def comentar(plan, actor, texto, linea=None):
    """Cualquiera que vea el plan comenta sobre su entidad (los Jefes de Área, p. ej.)."""
    texto = (texto or "").strip()
    _exigir(texto, "Escribe el comentario.")
    plan = _actual(plan)
    _exigir(plan.estado != E.PUBLICADO, "El plan ya está publicado.")
    if actor.es_global:
        facultad = linea.facultad if linea else None
        cum_fum = linea.cum_fum if linea else None
    else:
        facultad, cum_fum = actor.facultad, actor.cum_fum
        _exigir(linea is None or es_de_su_entidad(actor, linea.facultad, linea.cum_fum), "Esa línea no es de tu entidad.")
    return ComentarioPlan.objects.create(plan=plan, facultad=facultad, cum_fum=cum_fum, linea=linea, texto=texto, usuario=actor)


# --- Revisión de la CI (RF-035) ---------------------------------------------------------


@transaction.atomic
def cerrar_revision(plan, actor, forzar=False):
    """Pasa a la revisión de la CI. Con `forzar`, las entidades que no enviaron conservan la propuesta inicial."""
    _exigir_ci(actor)
    plan = _bloquear(plan)
    _exigir_estado(plan, E.ENVIADO)
    pendientes = plan.entidades.exclude(estado=PlanEntidad.Estado.PROPUESTA_ENVIADA)
    if pendientes.exists() and not forzar:
        nombres = ", ".join(str(e.entidad) for e in pendientes.select_related("facultad", "cum_fum")[:10])
        raise ErrorDeNegocio(f"Faltan propuestas de: {nombres}. Puedes esperar o forzar el paso a la revisión.")

    for entidad_plan in pendientes:
        filtro = {"facultad": entidad_plan.facultad} if entidad_plan.facultad_id else {"cum_fum": entidad_plan.cum_fum}
        lineas = plan.lineas.filter(**filtro)
        lineas.filter(origen=LineaPlan.Origen.ENTIDAD).delete()
        lineas.update(accion_entidad=A.ACEPTAR, plazas_entidad=None, comentario_entidad="")

    plan.estado = E.REVISION_CI
    plan.save(update_fields=["estado"])
    detalle = f"Sin propuesta (conservan la inicial): {pendientes.count()} entidades" if forzar and pendientes.exists() else ""
    _registrar(plan, actor, "Cerró la revisión de las entidades", comentario=detalle)
    return plan


def decidir(linea, decision, plazas, comentario, actor):
    _exigir_ci(actor)
    linea.plan = _actual(linea.plan_id)
    _exigir_estado(linea.plan, E.REVISION_CI)
    _exigir(decision in D.values, "Decisión no válida.")
    comentario = (comentario or "").strip()
    if decision == D.OTRO:
        _exigir(plazas is not None, "Indica la cantidad de plazas.")
    if decision != D.ACEPTAR:
        _exigir(comentario, "Justifica la decisión con un comentario (RF-035).")

    antes = _texto_plazas(linea.resultado())
    linea.decision_ci = decision
    linea.plazas_decision = plazas if decision == D.OTRO else None
    linea.comentario_ci = comentario
    linea.save(update_fields=["decision_ci", "plazas_decision", "comentario_ci"])
    _registrar(linea.plan, actor, f"La CI: {D(decision).label.lower()}", linea, antes, _texto_plazas(linea.resultado()), comentario)
    return linea


@transaction.atomic
def generar_version_final(plan, actor):
    """RF-035: fija las plazas aprobadas de cada línea y lo pasa al Vicerrector."""
    _exigir_ci(actor)
    plan = _bloquear(plan)
    _exigir_estado(plan, E.REVISION_CI)
    for linea in plan.lineas.all():
        linea.plazas_aprobadas = linea.resultado()
        linea.save(update_fields=["plazas_aprobadas"])
    plan.version += 1
    plan.estado = E.EN_APROBACION
    plan.observaciones_vicerrector = ""
    plan.save(update_fields=["version", "estado", "observaciones_vicerrector"])
    _registrar(plan, actor, f"Generó la versión final {plan.version}")

    vicerrectores = Usuario.objects.filter(is_active=True, rol__codigo="vicerrector")
    notificar(vicerrectores, "plan_para_aprobacion", {"anio": plan.anio_academico, "version": plan.version})
    return plan


# --- Aprobación (RF-036) ------------------------------------------------------------------


@transaction.atomic
def aprobar(plan, actor):
    """La aprobación del Vicerrector publica el plan (decisión del cliente) y fija las plazas de la oferta."""
    _exigir(es_vicerrector(actor), "Solo el Vicerrector de Formación aprueba el plan de plazas.")
    plan = _bloquear(plan)
    _exigir_estado(plan, E.EN_APROBACION)

    for linea in plan.lineas.select_related("oferta"):
        oferta = linea.oferta or OfertaCarrera.objects.filter(
            carrera=linea.carrera, facultad=linea.facultad, cum_fum=linea.cum_fum, anio_academico=plan.anio_academico
        ).first()
        if linea.plazas_aprobadas is None:
            # Sale del plan: la oferta se conserva (historial de interés) pero sin plazas.
            if oferta is not None:
                OfertaCarrera.objects.filter(pk=oferta.pk).update(plazas_plan=None)
            continue
        if oferta is None:
            oferta = OfertaCarrera.objects.create(
                carrera=linea.carrera, facultad=linea.facultad, cum_fum=linea.cum_fum, anio_academico=plan.anio_academico,
                asignada_por_ci=True, creada_por=actor,
            )
        oferta.plazas_plan = linea.plazas_aprobadas
        oferta.save(update_fields=["plazas_plan"])
        if linea.oferta_id != oferta.pk:
            linea.oferta = oferta
            linea.save(update_fields=["oferta"])

    plan.estado = E.PUBLICADO
    plan.aprobado_por = actor
    plan.fecha_aprobacion = timezone.now()
    plan.save(update_fields=["estado", "aprobado_por", "fecha_aprobacion"])
    _registrar(plan, actor, "Aprobó y publicó el plan")

    destinatarios = _usuarios_con_permiso("plan_plazas", "ver").filter(rol__isnull=False).distinct()
    notificar(destinatarios, "plan_publicado", {"anio": plan.anio_academico})
    return plan


@transaction.atomic
def devolver(plan, actor, observaciones):
    _exigir(es_vicerrector(actor), "Solo el Vicerrector de Formación devuelve el plan.")
    plan = _bloquear(plan)
    _exigir_estado(plan, E.EN_APROBACION)
    observaciones = (observaciones or "").strip()
    _exigir(observaciones, "Escribe las observaciones para la Comisión de Ingreso.")
    plan.estado = E.REVISION_CI
    plan.observaciones_vicerrector = observaciones
    plan.save(update_fields=["estado", "observaciones_vicerrector"])
    _registrar(plan, actor, "Devolvió el plan con observaciones", comentario=observaciones)

    comision = [u for u in _usuarios_con_permiso("plan_plazas", "editar").distinct() if es_ci(u) and not u.is_superuser]
    notificar(comision, "plan_devuelto", {"anio": plan.anio_academico, "observaciones": observaciones})
    return plan
