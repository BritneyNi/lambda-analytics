"""
Modelos del Dashboard Analítico para el sector construcción.
Lambda Analytics - Prueba Técnica
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Proyecto(models.Model):
    """Representa un proyecto de construcción."""

    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("pausado", "Pausado"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ]

    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField(blank=True)
    cliente = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="activo", db_index=True)
    fecha_inicio = models.DateField()
    fecha_fin_estimada = models.DateField()
    fecha_fin_real = models.DateField(null=True, blank=True)
    presupuesto = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    costo_actual = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    avance_porcentaje = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje de avance entre 0 y 100",
    )
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="proyectos_responsable"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado", "-avance_porcentaje"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"

    @property
    def desviacion_presupuesto(self):
        """Retorna la desviación de costo respecto al presupuesto en porcentaje."""
        if self.presupuesto == 0:
            return 0
        return float((self.costo_actual - self.presupuesto) / self.presupuesto * 100)

    @property
    def dias_restantes(self):
        """Días restantes hasta la fecha de fin estimada."""
        return (self.fecha_fin_estimada - timezone.now().date()).days


class Actividad(models.Model):
    """Actividad o tarea dentro de un proyecto."""

    PRIORIDAD_CHOICES = [
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    ]

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_progreso", "En progreso"),
        ("completada", "Completada"),
        ("bloqueada", "Bloqueada"),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="actividades")
    nombre = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default="media")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="pendiente", db_index=True)
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="actividades"
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    avance_porcentaje = models.FloatField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ["-prioridad", "fecha_vencimiento"]

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"

    @property
    def esta_vencida(self):
        if self.fecha_vencimiento and self.estado != "completada":
            return self.fecha_vencimiento < timezone.now().date()
        return False


class Indicador(models.Model):
    """KPI o indicador de rendimiento asociado a un proyecto."""

    TIPO_CHOICES = [
        ("porcentaje", "Porcentaje"),
        ("numero", "Número"),
        ("moneda", "Moneda"),
        ("dias", "Días"),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="indicadores")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default="numero")
    valor_actual = models.FloatField()
    valor_objetivo = models.FloatField()
    umbral_critico = models.FloatField(
        help_text="Valor por debajo del cual el indicador se considera crítico"
    )
    # timezone.now sin paréntesis: Django llama la función en cada instancia nueva,
    # no en tiempo de importación del módulo.
    fecha_medicion = models.DateField(default=timezone.now)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Indicador"
        verbose_name_plural = "Indicadores"
        ordering = ["-fecha_medicion"]

    def __str__(self):
        return f"{self.nombre}: {self.valor_actual} / {self.valor_objetivo}"

    @property
    def es_critico(self):
        """True si el valor actual está por debajo del umbral crítico."""
        return self.valor_actual < self.umbral_critico

    @property
    def rendimiento_porcentaje(self):
        """Porcentaje de cumplimiento respecto al objetivo."""
        if self.valor_objetivo == 0:
            return 0
        return (self.valor_actual / self.valor_objetivo) * 100


class Reporte(models.Model):
    """Reporte generado para un proyecto en un período dado."""

    TIPO_CHOICES = [
        ("semanal", "Semanal"),
        ("mensual", "Mensual"),
        ("trimestral", "Trimestral"),
        ("final", "Final"),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="reportes")
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    contenido = models.JSONField(
        default=dict, help_text="Datos del reporte en formato JSON estructurado"
    )
    generado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="reportes_generados"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"
        ordering = ["-creado_en"]
        unique_together = [("proyecto", "tipo", "periodo_inicio")]

    def __str__(self):
        return f"Reporte {self.get_tipo_display()} - {self.proyecto.nombre} ({self.periodo_inicio})"
