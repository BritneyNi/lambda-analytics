"""
ViewSets para la API del Dashboard Analítico.
Incluye acciones personalizadas, filtros, paginación y ordenamiento.
"""
from django.db.models import Avg, Count, Q
from django.utils import timezone

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters as df_filters

from .models import Proyecto, Actividad, Indicador, Reporte
from .serializers import (
    ProyectoListSerializer,
    ProyectoDetailSerializer,
    ActividadSerializer,
    IndicadorSerializer,
    ReporteSerializer,
    DashboardResumenSerializer,
)


# ─── Filtros ──────────────────────────────────────────────────────────────────

class ProyectoFilter(FilterSet):
    avance_min = df_filters.NumberFilter(field_name="avance_porcentaje", lookup_expr="gte")
    avance_max = df_filters.NumberFilter(field_name="avance_porcentaje", lookup_expr="lte")
    fecha_inicio_desde = df_filters.DateFilter(field_name="fecha_inicio", lookup_expr="gte")
    fecha_inicio_hasta = df_filters.DateFilter(field_name="fecha_inicio", lookup_expr="lte")

    class Meta:
        model = Proyecto
        fields = ["estado", "cliente", "responsable"]


class ActividadFilter(FilterSet):
    vencidas = df_filters.BooleanFilter(method="filtrar_vencidas")

    class Meta:
        model = Actividad
        fields = ["proyecto", "estado", "prioridad", "responsable"]

    def filtrar_vencidas(self, queryset, name, value):
        hoy = timezone.now().date()
        if value:
            return queryset.filter(fecha_vencimiento__lt=hoy).exclude(estado="completada")
        return queryset.exclude(
            fecha_vencimiento__lt=hoy
        ).exclude(estado="completada")


# ─── ViewSets ─────────────────────────────────────────────────────────────────

class ProyectoViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para Proyectos.
    Incluye filtros por estado, cliente, avance y fechas.
    Soporta búsqueda por nombre y descripción.
    Permite ordenamiento por avance, fechas y presupuesto.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProyectoFilter
    search_fields = ["nombre", "descripcion", "cliente"]
    ordering_fields = ["avance_porcentaje", "fecha_inicio", "fecha_fin_estimada", "presupuesto", "creado_en"]
    ordering = ["-creado_en"]

    def get_queryset(self):
        return Proyecto.objects.select_related("responsable").annotate(
            total_actividades=Count("actividades"),
            actividades_completadas=Count(
                "actividades", filter=Q(actividades__estado="completada")
            ),
        )

    def get_serializer_class(self):
        if self.action in ("list",):
            return ProyectoListSerializer
        return ProyectoDetailSerializer

    def perform_create(self, serializer):
        serializer.save(responsable=self.request.user)

    @action(detail=True, methods=["post"], url_path="actualizar-avance")
    def actualizar_avance(self, request, pk=None):
        """
        POST /api/proyectos/{id}/actualizar-avance/
        Actualiza el porcentaje de avance de un proyecto.
        """
        proyecto = self.get_object()
        avance = request.data.get("avance_porcentaje")
        if avance is None:
            return Response(
                {"error": "El campo avance_porcentaje es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            avance = float(avance)
        except (TypeError, ValueError):
            return Response(
                {"error": "avance_porcentaje debe ser un número."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= avance <= 100):
            return Response(
                {"error": "avance_porcentaje debe estar entre 0 y 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proyecto.avance_porcentaje = avance
        if avance == 100 and proyecto.estado == "activo":
            proyecto.estado = "completado"
            proyecto.fecha_fin_real = timezone.now().date()
        proyecto.save(update_fields=["avance_porcentaje", "estado", "fecha_fin_real"])
        serializer = ProyectoDetailSerializer(proyecto, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="resumen")
    def resumen(self, request, pk=None):
        """
        GET /api/proyectos/{id}/resumen/
        Retorna un resumen ejecutivo del proyecto: KPIs, actividades e indicadores.
        """
        proyecto = self.get_object()
        actividades = proyecto.actividades.all()
        indicadores = proyecto.indicadores.all()
        hoy = timezone.now().date()

        data = {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "estado": proyecto.estado,
            "avance_porcentaje": proyecto.avance_porcentaje,
            "dias_restantes": proyecto.dias_restantes,
            "desviacion_presupuesto": proyecto.desviacion_presupuesto,
            "actividades": {
                "total": actividades.count(),
                "completadas": actividades.filter(estado="completada").count(),
                "en_progreso": actividades.filter(estado="en_progreso").count(),
                "vencidas": actividades.filter(
                    fecha_vencimiento__lt=hoy
                ).exclude(estado="completada").count(),
            },
            "indicadores": {
                "total": indicadores.count(),
                "criticos": sum(1 for i in indicadores if i.es_critico),
                "promedio_rendimiento": (
                    sum(i.rendimiento_porcentaje for i in indicadores) / indicadores.count()
                    if indicadores.exists() else 0
                ),
            },
        }
        return Response(data)


class ActividadViewSet(viewsets.ModelViewSet):
    """CRUD completo para Actividades con filtros por proyecto, estado y prioridad."""

    permission_classes = [IsAuthenticated]
    serializer_class = ActividadSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ActividadFilter
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["prioridad", "fecha_vencimiento", "avance_porcentaje", "creado_en"]
    ordering = ["-prioridad", "fecha_vencimiento"]

    def get_queryset(self):
        return Actividad.objects.select_related("proyecto", "responsable")


class IndicadorViewSet(viewsets.ModelViewSet):
    """CRUD para Indicadores con soporte para filtrar por proyecto y criticidad."""

    permission_classes = [IsAuthenticated]
    serializer_class = IndicadorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["proyecto", "tipo"]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["fecha_medicion", "valor_actual"]
    ordering = ["-fecha_medicion"]

    def get_queryset(self):
        qs = Indicador.objects.select_related("proyecto")
        solo_criticos = self.request.query_params.get("criticos")
        if solo_criticos and solo_criticos.lower() in ("true", "1"):
            # Filtramos en Python porque es_critico es una property
            ids_criticos = [i.id for i in qs if i.es_critico]
            return qs.filter(id__in=ids_criticos)
        return qs


class ReporteViewSet(viewsets.ModelViewSet):
    """CRUD para Reportes con filtros por proyecto y tipo."""

    permission_classes = [IsAuthenticated]
    serializer_class = ReporteSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["proyecto", "tipo"]
    ordering_fields = ["creado_en", "periodo_inicio"]
    ordering = ["-creado_en"]

    def get_queryset(self):
        return Reporte.objects.select_related("proyecto", "generado_por")

    def perform_create(self, serializer):
        serializer.save(generado_por=self.request.user)


# ─── Dashboard Resumen Global ─────────────────────────────────────────────────

class DashboardViewSet(viewsets.ViewSet):
    """
    Endpoints de resumen global del dashboard.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """
        GET /api/dashboard/resumen/
        Retorna:
          - Total de proyectos activos
          - Promedio de avance por proyecto
          - Top 5 proyectos por rendimiento
          - Indicadores críticos (debajo del umbral)
        """
        proyectos_activos = Proyecto.objects.filter(estado="activo")

        # Promedio de avance
        promedio = proyectos_activos.aggregate(avg=Avg("avance_porcentaje"))["avg"] or 0.0

        # Top 5 por avance
        top_proyectos = proyectos_activos.order_by("-avance_porcentaje")[:5]

        # Indicadores críticos: valor_actual < umbral_critico
        todos_indicadores = Indicador.objects.select_related("proyecto").all()
        indicadores_criticos = [
            {
                "id": ind.id,
                "nombre": ind.nombre,
                "proyecto_nombre": ind.proyecto.nombre,
                "valor_actual": ind.valor_actual,
                "valor_objetivo": ind.valor_objetivo,
                "rendimiento_porcentaje": ind.rendimiento_porcentaje,
            }
            for ind in todos_indicadores
            if ind.es_critico
        ]

        # Actividades vencidas
        hoy = timezone.now().date()
        actividades_vencidas = Actividad.objects.filter(
            fecha_vencimiento__lt=hoy
        ).exclude(estado="completada").count()

        # Proyectos por estado
        proyectos_por_estado = dict(
            Proyecto.objects.values("estado").annotate(total=Count("id")).values_list("estado", "total")
        )

        data = {
            "total_proyectos_activos": proyectos_activos.count(),
            "promedio_avance": round(promedio, 2),
            "top_proyectos": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "cliente": p.cliente,
                    "avance_porcentaje": p.avance_porcentaje,
                    "estado": p.estado,
                }
                for p in top_proyectos
            ],
            "indicadores_criticos": indicadores_criticos,
            "total_actividades_vencidas": actividades_vencidas,
            "proyectos_por_estado": proyectos_por_estado,
        }

        serializer = DashboardResumenSerializer(data)
        return Response(serializer.data)
