"""Plan de plazas (RF-032 a RF-039).

Estados del plan:
    borrador → enviado → revision_ci → en_aprobacion → publicado
                                ↑______ devolver ______|

- borrador: la Comisión de Ingreso (CI) arma la propuesta inicial.
- enviado: cada entidad revisa sus líneas y envía su propuesta (RF-034).
  El avance de cada entidad está en `PlanEntidad.estado`
  (pendiente → en_revision → propuesta_enviada).
- revision_ci: la CI decide el valor final de cada línea (RF-035).
- en_aprobacion: el Vicerrector aprueba, lo que publica el plan (RF-036), o lo devuelve.
- publicado: inmutable (RF-039). Los cambios van en una versión complementaria.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.oferta.models import validar_anio_academico


class PlanPlazas(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ENVIADO = "enviado", "Enviado a entidades"
        REVISION_CI = "revision_ci", "Revisión de la Comisión"
        EN_APROBACION = "en_aprobacion", "En aprobación"
        PUBLICADO = "publicado", "Publicado"

    anio_academico = models.CharField("año académico", max_length=9, validators=[validar_anio_academico], db_index=True)
    # Versión complementaria (RF-039): parte del plan publicado vigente del año.
    complementaria_de = models.ForeignKey(
        "self", verbose_name="complementaria de", null=True, blank=True, on_delete=models.PROTECT, related_name="complementarias"
    )
    estado = models.CharField("estado", max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    # Sube cada vez que la CI genera una versión final (RF-038).
    version = models.PositiveSmallIntegerField("versión", default=0)
    notas = models.TextField("notas", blank=True)
    observaciones_vicerrector = models.TextField("observaciones del Vicerrector", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="creado por", null=True, on_delete=models.SET_NULL, related_name="+")
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aprobado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    fecha_aprobacion = models.DateTimeField("fecha de aprobación", null=True, blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "plan de plazas"
        verbose_name_plural = "planes de plazas"
        ordering = ["-anio_academico", "-created_at"]
        constraints = [
            # Un solo plan base por año; las complementarias cuelgan de él.
            models.UniqueConstraint(fields=["anio_academico"], condition=Q(complementaria_de__isnull=True), name="un_plan_base_por_anio"),
        ]

    def __str__(self):
        tipo = "complementario " if self.complementaria_de_id else ""
        return f"Plan de plazas {tipo}{self.anio_academico}"

    @property
    def es_complementario(self) -> bool:
        return self.complementaria_de_id is not None


class EntidadEnPlan:
    """Campos comunes para apuntar a una Facultad o a un CUM/FUM (una de las dos)."""

    @property
    def entidad(self):
        return self.facultad or self.cum_fum


def _restriccion_una_entidad(nombre):
    return models.CheckConstraint(
        condition=(Q(facultad__isnull=False) & Q(cum_fum__isnull=True)) | (Q(facultad__isnull=True) & Q(cum_fum__isnull=False)),
        name=nombre,
    )


class PlanEntidad(EntidadEnPlan, models.Model):
    """Avance de una entidad en la revisión del plan (pasos 22 y 23 de 7.3)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En revisión"
        PROPUESTA_ENVIADA = "propuesta_enviada", "Propuesta enviada"

    plan = models.ForeignKey(PlanPlazas, verbose_name="plan", on_delete=models.CASCADE, related_name="entidades")
    facultad = models.ForeignKey("nomencladores.Facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cum_fum = models.ForeignKey("nomencladores.CumFum", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    estado = models.CharField("estado", max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    comentario = models.TextField("comentario general", blank=True)
    enviada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    enviada_at = models.DateTimeField("enviada el", null=True, blank=True)

    class Meta:
        verbose_name = "entidad en el plan"
        verbose_name_plural = "entidades en el plan"
        constraints = [
            _restriccion_una_entidad("plan_entidad_una_entidad"),
            models.UniqueConstraint(fields=["plan", "facultad"], condition=Q(facultad__isnull=False), name="plan_entidad_unica_facultad"),
            models.UniqueConstraint(fields=["plan", "cum_fum"], condition=Q(cum_fum__isnull=False), name="plan_entidad_unica_cum_fum"),
        ]


class LineaPlan(EntidadEnPlan, models.Model):
    """Plazas de una carrera en una entidad (Plan_Plazas_Detalle del modelo conceptual)."""

    class Origen(models.TextChoices):
        CI = "ci", "Comisión de Ingreso"
        ENTIDAD = "entidad", "Solicitada por la entidad"

    class AccionEntidad(models.TextChoices):
        ACEPTAR = "aceptar", "Acepta"
        MODIFICAR = "modificar", "Modifica la cantidad"
        QUITAR = "quitar", "Solicita quitarla"
        AGREGAR = "agregar", "Solicita agregarla"

    class DecisionCI(models.TextChoices):
        ACEPTAR = "aceptar", "Acepta la propuesta de la entidad"
        MANTENER = "mantener", "Mantiene la propuesta inicial"
        OTRO = "otro", "Fija otra cantidad"

    plan = models.ForeignKey(PlanPlazas, verbose_name="plan", on_delete=models.CASCADE, related_name="lineas")
    carrera = models.ForeignKey("nomencladores.Carrera", verbose_name="carrera", on_delete=models.PROTECT, related_name="+")
    facultad = models.ForeignKey("nomencladores.Facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cum_fum = models.ForeignKey("nomencladores.CumFum", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # Se vincula al publicar; las carreras nuevas aceptadas crean su oferta.
    oferta = models.ForeignKey("oferta.OfertaCarrera", null=True, blank=True, on_delete=models.PROTECT, related_name="lineas_plan")
    origen = models.CharField("origen", max_length=10, choices=Origen.choices, default=Origen.CI)

    plazas_propuestas = models.PositiveIntegerField("propuesta de la CI", default=0)
    accion_entidad = models.CharField("acción de la entidad", max_length=10, choices=AccionEntidad.choices, default=AccionEntidad.ACEPTAR)
    plazas_entidad = models.PositiveIntegerField("propuesta de la entidad", null=True, blank=True)
    comentario_entidad = models.TextField("comentario de la entidad", blank=True)

    decision_ci = models.CharField("decisión de la CI", max_length=10, choices=DecisionCI.choices, default=DecisionCI.ACEPTAR)
    plazas_decision = models.PositiveIntegerField("cantidad fijada por la CI", null=True, blank=True, validators=[MinValueValidator(0)])
    comentario_ci = models.TextField("comentario de la CI", blank=True)
    # Resultado: se calcula al generar la versión final. Null = la carrera sale del plan.
    plazas_aprobadas = models.PositiveIntegerField("plazas aprobadas", null=True, blank=True)

    class Meta:
        verbose_name = "línea del plan"
        verbose_name_plural = "líneas del plan"
        ordering = ["carrera__nombre", "id"]
        constraints = [
            _restriccion_una_entidad("linea_plan_una_entidad"),
            models.UniqueConstraint(fields=["plan", "carrera", "facultad"], condition=Q(facultad__isnull=False), name="linea_unica_facultad"),
            models.UniqueConstraint(fields=["plan", "carrera", "cum_fum"], condition=Q(cum_fum__isnull=False), name="linea_unica_cum_fum"),
        ]

    def __str__(self):
        return f"{self.carrera} — {self.entidad}"

    def propuesta_de_la_entidad(self):
        """Cantidad que propone la entidad (None si pide quitarla)."""
        if self.accion_entidad == self.AccionEntidad.QUITAR:
            return None
        if self.accion_entidad in (self.AccionEntidad.MODIFICAR, self.AccionEntidad.AGREGAR):
            return self.plazas_entidad
        return self.plazas_propuestas

    def resultado(self):
        """Plazas finales según la decisión de la CI (None = sale del plan)."""
        if self.decision_ci == self.DecisionCI.OTRO:
            return self.plazas_decision
        if self.decision_ci == self.DecisionCI.MANTENER:
            # Mantener una carrera que la entidad pidió agregar es no incluirla.
            return None if self.origen == self.Origen.ENTIDAD else self.plazas_propuestas
        return self.propuesta_de_la_entidad()


class HistorialPlan(models.Model):
    """Cada cambio del plan (RF-038): quién, cuándo, qué valía antes, qué vale ahora y por qué."""

    plan = models.ForeignKey(PlanPlazas, verbose_name="plan", on_delete=models.CASCADE, related_name="historial")
    version = models.PositiveSmallIntegerField("versión")
    linea = models.ForeignKey(LineaPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    descripcion_linea = models.CharField("línea", max_length=255, blank=True)
    accion = models.CharField("acción", max_length=120)
    valor_anterior = models.CharField("valor anterior", max_length=120, blank=True)
    valor_nuevo = models.CharField("valor nuevo", max_length=120, blank=True)
    comentario = models.TextField("comentario", blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    usuario_nombre = models.CharField("usuario", max_length=150, blank=True)
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "cambio del plan"
        verbose_name_plural = "historial del plan"
        ordering = ["-created_at", "-id"]


class ComentarioPlan(EntidadEnPlan, models.Model):
    """Comentario sobre el plan de una entidad (lo usan, p. ej., los Jefes de Área)."""

    plan = models.ForeignKey(PlanPlazas, on_delete=models.CASCADE, related_name="comentarios")
    facultad = models.ForeignKey("nomencladores.Facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cum_fum = models.ForeignKey("nomencladores.CumFum", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    linea = models.ForeignKey(LineaPlan, null=True, blank=True, on_delete=models.CASCADE, related_name="comentarios")
    texto = models.TextField("comentario")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "comentario del plan"
        verbose_name_plural = "comentarios del plan"
        ordering = ["created_at", "id"]
