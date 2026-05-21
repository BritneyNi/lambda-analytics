from django.db.models import Avg, Count, Q
from django.utils import timezone

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import Proyecto, Actividad, Indicador, Reporte
from .serializers import (
    ProyectoSerializer,
    ProyectoDetalleSerializer,
    ActividadSerializer,
    IndicadorSerializer,
    ReporteSerializer,
)


class ProyectoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "cliente"]
    search_fields = ["nombre", "cliente"]
    ordering_fields = ["avance_porcentaje", "fecha_inicio", "creado_en"]
    ordering = ["-creado_en"]

    def get_queryset(self):
        return Proyecto.objects.select_related("responsable").all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProyectoDetalleSerializer
        return ProyectoSerializer

    def perform_create(self, serializer):
        serializer.save(responsable=self.request.user)

    @action(detail=True, methods=["post"], url_path="actualizar-avance")
    def actualizar_avance(self, request, pk=None):
        proyecto = self.get_object()
        avance = request.data.get("avance_porcentaje")

        if avance is None:
            return Response(
                {"error": "El campo avance_porcentaje es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            avance = float(avance)
        except ValueError:
            return Response(
                {"error": "avance_porcentaje debe ser un numero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (0 <= avance <= 100):
            return Response(
                {"error": "El avance debe estar entre 0 y 100"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proyecto.avance_porcentaje = avance
        if avance == 100:
            proyecto.estado = "completado"
            proyecto.fecha_fin_real = timezone.now().date()
        proyecto.save()

        serializer = ProyectoSerializer(proyecto, context={"request": request})
        return Response(serializer.data)


class ActividadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ActividadSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["proyecto", "estado", "prioridad"]
    search_fields = ["nombre"]
    ordering = ["-creado_en"]

    def get_queryset(self):
        return Actividad.objects.select_related("proyecto", "responsable").all()


class IndicadorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = IndicadorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["proyecto", "tipo"]

    def get_queryset(self):
        return Indicador.objects.select_related("proyecto").all()


class ReporteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReporteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["proyecto", "tipo"]

    def get_queryset(self):
        return Reporte.objects.select_related("proyecto").all()

    def perform_create(self, serializer):
        serializer.save(generado_por=self.request.user)


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        proyectos_activos = Proyecto.objects.filter(estado="activo")
        promedio = proyectos_activos.aggregate(avg=Avg("avance_porcentaje"))["avg"] or 0

        top_proyectos = proyectos_activos.order_by("-avance_porcentaje")[:5]

        # indicadores criticos
        todos = Indicador.objects.select_related("proyecto").all()
        criticos = [i for i in todos if i.es_critico]

        hoy = timezone.now().date()
        vencidas = Actividad.objects.filter(
            fecha_vencimiento__lt=hoy
        ).exclude(estado="completada").count()

        data = {
            "total_proyectos_activos": proyectos_activos.count(),
            "promedio_avance": round(promedio, 2),
            "top_proyectos": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "avance_porcentaje": p.avance_porcentaje,
                    "estado": p.estado,
                }
                for p in top_proyectos
            ],
            "indicadores_criticos": [
                {
                    "id": i.id,
                    "nombre": i.nombre,
                    "proyecto": i.proyecto.nombre,
                    "valor_actual": i.valor_actual,
                    "valor_objetivo": i.valor_objetivo,
                }
                for i in criticos
            ],
            "actividades_vencidas": vencidas,
        }

        return Response(data)