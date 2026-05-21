"""
Serializers para la API del Dashboard Analítico.
Incluye validaciones de negocio y representaciones anidadas.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Proyecto, Actividad, Indicador, Reporte


class UserResumenSerializer(serializers.ModelSerializer):
    """Representación compacta de un usuario."""

    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "nombre_completo"]

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username


# ─── Indicador ────────────────────────────────────────────────────────────────

class IndicadorSerializer(serializers.ModelSerializer):
    es_critico = serializers.ReadOnlyField()
    rendimiento_porcentaje = serializers.ReadOnlyField()

    class Meta:
        model = Indicador
        fields = [
            "id", "proyecto", "nombre", "descripcion", "tipo",
            "valor_actual", "valor_objetivo", "umbral_critico",
            "fecha_medicion", "es_critico", "rendimiento_porcentaje",
            "creado_en",
        ]
        read_only_fields = ["creado_en"]

    def validate(self, data):
        """El umbral crítico no puede superar el valor objetivo."""
        umbral = data.get("umbral_critico", getattr(self.instance, "umbral_critico", None))
        objetivo = data.get("valor_objetivo", getattr(self.instance, "valor_objetivo", None))
        if umbral is not None and objetivo is not None and umbral > objetivo:
            raise serializers.ValidationError(
                {"umbral_critico": "El umbral crítico no puede ser mayor que el valor objetivo."}
            )
        return data


# ─── Actividad ────────────────────────────────────────────────────────────────

class ActividadSerializer(serializers.ModelSerializer):
    responsable_detalle = UserResumenSerializer(source="responsable", read_only=True)
    esta_vencida = serializers.ReadOnlyField()

    class Meta:
        model = Actividad
        fields = [
            "id", "proyecto", "nombre", "descripcion", "prioridad", "estado",
            "responsable", "responsable_detalle", "fecha_inicio", "fecha_vencimiento",
            "avance_porcentaje", "esta_vencida", "creado_en", "actualizado_en",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]

    def validate(self, data):
        inicio = data.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        vencimiento = data.get("fecha_vencimiento", getattr(self.instance, "fecha_vencimiento", None))
        if inicio and vencimiento and inicio > vencimiento:
            raise serializers.ValidationError(
                {"fecha_vencimiento": "La fecha de vencimiento debe ser posterior a la fecha de inicio."}
            )
        return data


# ─── Reporte ──────────────────────────────────────────────────────────────────

class ReporteSerializer(serializers.ModelSerializer):
    generado_por_detalle = UserResumenSerializer(source="generado_por", read_only=True)

    class Meta:
        model = Reporte
        fields = [
            "id", "proyecto", "tipo", "periodo_inicio", "periodo_fin",
            "contenido", "generado_por", "generado_por_detalle", "creado_en",
        ]
        read_only_fields = ["creado_en"]

    def validate(self, data):
        inicio = data.get("periodo_inicio", getattr(self.instance, "periodo_inicio", None))
        fin = data.get("periodo_fin", getattr(self.instance, "periodo_fin", None))
        if inicio and fin and inicio > fin:
            raise serializers.ValidationError(
                {"periodo_fin": "El período fin debe ser posterior al período inicio."}
            )
        return data


# ─── Proyecto ─────────────────────────────────────────────────────────────────

class ProyectoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados."""

    responsable_detalle = UserResumenSerializer(source="responsable", read_only=True)
    desviacion_presupuesto = serializers.ReadOnlyField()
    dias_restantes = serializers.ReadOnlyField()
    total_actividades = serializers.IntegerField(read_only=True)
    actividades_completadas = serializers.IntegerField(read_only=True)

    class Meta:
        model = Proyecto
        fields = [
            "id", "nombre", "cliente", "estado", "avance_porcentaje",
            "fecha_inicio", "fecha_fin_estimada", "presupuesto", "costo_actual",
            "desviacion_presupuesto", "dias_restantes", "responsable_detalle",
            "total_actividades", "actividades_completadas",
        ]


class ProyectoDetailSerializer(serializers.ModelSerializer):
    """Serializer completo con relaciones anidadas."""

    responsable_detalle = UserResumenSerializer(source="responsable", read_only=True)
    actividades = ActividadSerializer(many=True, read_only=True)
    indicadores = IndicadorSerializer(many=True, read_only=True)
    reportes = ReporteSerializer(many=True, read_only=True)
    desviacion_presupuesto = serializers.ReadOnlyField()
    dias_restantes = serializers.ReadOnlyField()

    class Meta:
        model = Proyecto
        fields = [
            "id", "nombre", "descripcion", "cliente", "estado",
            "fecha_inicio", "fecha_fin_estimada", "fecha_fin_real",
            "presupuesto", "costo_actual", "avance_porcentaje",
            "desviacion_presupuesto", "dias_restantes",
            "responsable", "responsable_detalle",
            "actividades", "indicadores", "reportes",
            "creado_en", "actualizado_en",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]

    def validate_avance_porcentaje(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("El avance debe estar entre 0 y 100.")
        return value

    def validate(self, data):
        inicio = data.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fin_est = data.get("fecha_fin_estimada", getattr(self.instance, "fecha_fin_estimada", None))
        if inicio and fin_est and inicio > fin_est:
            raise serializers.ValidationError(
                {"fecha_fin_estimada": "La fecha de fin estimada debe ser posterior a la fecha de inicio."}
            )

        presupuesto = data.get("presupuesto", getattr(self.instance, "presupuesto", None))
        costo = data.get("costo_actual", getattr(self.instance, "costo_actual", 0))
        if presupuesto is not None and costo > presupuesto * 2:
            raise serializers.ValidationError(
                {"costo_actual": "El costo actual supera el doble del presupuesto. Verifique los datos."}
            )
        return data


# ─── Dashboard Resumen ────────────────────────────────────────────────────────

class IndicadorCriticoSerializer(serializers.Serializer):
    """Indicador crítico para el resumen del dashboard."""
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    proyecto_nombre = serializers.CharField()
    valor_actual = serializers.FloatField()
    valor_objetivo = serializers.FloatField()
    rendimiento_porcentaje = serializers.FloatField()


class ProyectoTopSerializer(serializers.Serializer):
    """Proyecto de alto rendimiento para el resumen."""
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    cliente = serializers.CharField()
    avance_porcentaje = serializers.FloatField()
    estado = serializers.CharField()


class DashboardResumenSerializer(serializers.Serializer):
    """Respuesta del endpoint GET /api/dashboard/resumen/"""
    total_proyectos_activos = serializers.IntegerField()
    promedio_avance = serializers.FloatField()
    top_proyectos = ProyectoTopSerializer(many=True)
    indicadores_criticos = IndicadorCriticoSerializer(many=True)
    total_actividades_vencidas = serializers.IntegerField()
    proyectos_por_estado = serializers.DictField(child=serializers.IntegerField())
