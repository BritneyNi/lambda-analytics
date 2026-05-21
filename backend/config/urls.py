"""
Configuración de URLs para la API del Dashboard.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import ProyectoViewSet, ActividadViewSet, IndicadorViewSet, ReporteViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r"proyectos", ProyectoViewSet, basename="proyecto")
router.register(r"actividades", ActividadViewSet, basename="actividad")
router.register(r"indicadores", IndicadorViewSet, basename="indicador")
router.register(r"reportes", ReporteViewSet, basename="reporte")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    # Autenticación JWT
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # API
    path("", include(router.urls)),
]
