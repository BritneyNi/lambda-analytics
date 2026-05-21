from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Proyecto(models.Model):
    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("pausado", "Pausado"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    cliente = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="activo")
    fecha_inicio = models.DateField()
    fecha_fin_estimada = models.DateField()
    fecha_fin_real = models.DateField(null=True, blank=True)
    presupuesto = models.DecimalField(max_digits=15, decimal_places=2)
    costo_actual = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avance_porcentaje = models.FloatField(default=0)
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="proyectos"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return self.nombre

    @property
    def dias_restantes(self):
        return (self.fecha_fin_estimada - timezone.now().date()).days

    @property
    def desviacion_presupuesto(self):
        if self.presupuesto == 0:
            return 0
        return float((self.costo_actual - self.presupuesto) / self.presupuesto * 100)


class Actividad(models.Model):
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
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="pendiente")
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="actividades"
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    avance_porcentaje = models.FloatField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"

    @property
    def esta_vencida(self):
        if self.fecha_vencimiento and self.estado != "completada":
            return self.fecha_vencimiento < timezone.now().date()
        return False


class Indicador(models.Model):
    TIPO_CHOICES = [
        ("porcentaje", "Porcentaje"),
        ("numero", "Número"),
        ("moneda", "Moneda"),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="indicadores")
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default="numero")
    valor_actual = models.FloatField()
    valor_objetivo = models.FloatField()
    umbral_critico = models.FloatField()
    fecha_medicion = models.DateField(default=timezone.now)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre}: {self.valor_actual}/{self.valor_objetivo}"

    @property
    def es_critico(self):
        return self.valor_actual < self.umbral_critico

    @property
    def rendimiento_porcentaje(self):
        if self.valor_objetivo == 0:
            return 0
        return (self.valor_actual / self.valor_objetivo) * 100


class Reporte(models.Model):
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
    # TODO: validar que periodo_fin > periodo_inicio
    contenido = models.JSONField(default=dict)
    generado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.proyecto.nombre}"