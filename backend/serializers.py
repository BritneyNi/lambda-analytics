from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Proyecto, Actividad, Indicador, Reporte


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class IndicadorSerializer(serializers.ModelSerializer):
    es_critico = serializers.ReadOnlyField()
    rendimiento_porcentaje = serializers.ReadOnlyField()

    class Meta:
        model = Indicador
        fields = "__all__"

    def validate(self, data):
        umbral = data.get("umbral_critico")
        objetivo = data.get("valor_objetivo")
        if umbral and objetivo and umbral > objetivo:
            raise serializers.ValidationError(
                "El umbral critico no puede ser mayor que el valor objetivo"
            )
        return data


class ActividadSerializer(serializers.ModelSerializer):
    esta_vencida = serializers.ReadOnlyField()

    class Meta:
        model = Actividad
        fields = "__all__"

    def validate(self, data):
        inicio = data.get("fecha_inicio")
        vencimiento = data.get("fecha_vencimiento")
        if inicio and vencimiento and inicio > vencimiento:
            raise serializers.ValidationError(
                "La fecha de vencimiento debe ser posterior a la fecha de inicio"
            )
        return data


class ReporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reporte
        fields = "__all__"


class ProyectoSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.SerializerMethodField()
    desviacion_presupuesto = serializers.ReadOnlyField()
    dias_restantes = serializers.ReadOnlyField()

    class Meta:
        model = Proyecto
        fields = "__all__"

    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return obj.responsable.get_full_name() or obj.responsable.username
        return None

    def validate(self, data):
        inicio = data.get("fecha_inicio")
        fin = data.get("fecha_fin_estimada")
        if inicio and fin and inicio > fin:
            raise serializers.ValidationError(
                "La fecha fin debe ser posterior a la fecha de inicio"
            )
        return data


class ProyectoDetalleSerializer(ProyectoSerializer):
    actividades = ActividadSerializer(many=True, read_only=True)
    indicadores = IndicadorSerializer(many=True, read_only=True)
    reportes = ReporteSerializer(many=True, read_only=True)