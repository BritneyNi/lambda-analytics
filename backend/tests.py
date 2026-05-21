"""
Tests unitarios para el Dashboard Analítico.
Ejecutar con: pytest --cov=dashboard --cov-report=term-missing
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from dashboard.models import Proyecto, Actividad, Indicador, Reporte


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="tester",
        email="tester@lambda.co",
        password="TestPass123!",
        first_name="Ana",
        last_name="García",
    )


@pytest.fixture
def token(api_client, usuario):
    response = api_client.post(
        "/api/auth/token/",
        {"username": "tester", "password": "TestPass123!"},
        format="json",
    )
    return response.data["access"]


@pytest.fixture
def cliente_autenticado(api_client, token):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def proyecto(db, usuario):
    return Proyecto.objects.create(
        nombre="Edificio Central",
        cliente="Constructora ABC",
        estado="activo",
        fecha_inicio=date.today() - timedelta(days=30),
        fecha_fin_estimada=date.today() + timedelta(days=90),
        presupuesto=500_000_000,
        costo_actual=120_000_000,
        avance_porcentaje=25.0,
        responsable=usuario,
    )


@pytest.fixture
def indicador(db, proyecto):
    return Indicador.objects.create(
        proyecto=proyecto,
        nombre="Avance físico",
        tipo="porcentaje",
        valor_actual=20.0,
        valor_objetivo=100.0,
        umbral_critico=30.0,  # valor_actual < umbral → crítico
    )


@pytest.fixture
def actividad(db, proyecto, usuario):
    return Actividad.objects.create(
        proyecto=proyecto,
        nombre="Excavación",
        prioridad="alta",
        estado="en_progreso",
        responsable=usuario,
        fecha_inicio=date.today() - timedelta(days=10),
        fecha_vencimiento=date.today() + timedelta(days=20),
        avance_porcentaje=50.0,
    )


# ─── Tests de modelos ─────────────────────────────────────────────────────────

class TestProyectoModel:

    def test_str_representation(self, proyecto):
        assert "Edificio Central" in str(proyecto)
        assert "Activo" in str(proyecto)

    def test_desviacion_presupuesto(self, proyecto):
        # costo_actual=120M, presupuesto=500M → desviación negativa
        assert proyecto.desviacion_presupuesto == pytest.approx(-76.0, abs=1)

    def test_dias_restantes_positivo(self, proyecto):
        assert proyecto.dias_restantes > 0

    def test_desviacion_con_presupuesto_cero(self, db, usuario):
        p = Proyecto(
            nombre="Test",
            cliente="C",
            estado="activo",
            fecha_inicio=date.today(),
            fecha_fin_estimada=date.today() + timedelta(days=10),
            presupuesto=0,
            costo_actual=0,
            responsable=usuario,
        )
        assert p.desviacion_presupuesto == 0


class TestIndicadorModel:

    def test_es_critico_cuando_valor_bajo(self, indicador):
        # valor_actual=20 < umbral_critico=30 → crítico
        assert indicador.es_critico is True

    def test_no_es_critico_cuando_valor_ok(self, indicador):
        indicador.valor_actual = 50.0
        assert indicador.es_critico is False

    def test_rendimiento_porcentaje(self, indicador):
        # 20 / 100 * 100 = 20%
        assert indicador.rendimiento_porcentaje == pytest.approx(20.0)

    def test_rendimiento_con_objetivo_cero(self, indicador):
        indicador.valor_objetivo = 0
        assert indicador.rendimiento_porcentaje == 0


class TestActividadModel:

    def test_no_vencida_con_fecha_futura(self, actividad):
        assert actividad.esta_vencida is False

    def test_vencida_con_fecha_pasada(self, actividad):
        actividad.fecha_vencimiento = date.today() - timedelta(days=1)
        assert actividad.esta_vencida is True

    def test_completada_no_vencida(self, actividad):
        actividad.fecha_vencimiento = date.today() - timedelta(days=5)
        actividad.estado = "completada"
        assert actividad.esta_vencida is False


# ─── Tests de API ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProyectoAPI:

    def test_listar_proyectos_requiere_auth(self, api_client):
        response = api_client.get("/api/proyectos/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listar_proyectos(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.get("/api/proyectos/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_crear_proyecto(self, cliente_autenticado):
        data = {
            "nombre": "Torre Norte",
            "cliente": "Inversiones XYZ",
            "estado": "activo",
            "fecha_inicio": str(date.today()),
            "fecha_fin_estimada": str(date.today() + timedelta(days=180)),
            "presupuesto": "1000000000",
            "costo_actual": "0",
            "avance_porcentaje": 0,
        }
        response = cliente_autenticado.post("/api/proyectos/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nombre"] == "Torre Norte"

    def test_crear_proyecto_fecha_invalida(self, cliente_autenticado):
        data = {
            "nombre": "Error Test",
            "cliente": "C",
            "estado": "activo",
            "fecha_inicio": str(date.today() + timedelta(days=10)),
            "fecha_fin_estimada": str(date.today()),  # antes del inicio
            "presupuesto": "100000",
            "costo_actual": "0",
            "avance_porcentaje": 0,
        }
        response = cliente_autenticado.post("/api/proyectos/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_actualizar_avance(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.post(
            f"/api/proyectos/{proyecto.id}/actualizar-avance/",
            {"avance_porcentaje": 60},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["avance_porcentaje"] == 60

    def test_actualizar_avance_completa_proyecto(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.post(
            f"/api/proyectos/{proyecto.id}/actualizar-avance/",
            {"avance_porcentaje": 100},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "completado"

    def test_filtrar_por_estado(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.get("/api/proyectos/?estado=activo")
        assert response.status_code == status.HTTP_200_OK
        for p in response.data["results"]:
            assert p["estado"] == "activo"

    def test_buscar_por_nombre(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.get("/api/proyectos/?search=Edificio")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1


@pytest.mark.django_db
class TestDashboardResumen:

    def test_resumen_retorna_estructura_correcta(self, cliente_autenticado, proyecto, indicador):
        response = cliente_autenticado.get("/api/dashboard/resumen/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_proyectos_activos" in data
        assert "promedio_avance" in data
        assert "top_proyectos" in data
        assert "indicadores_criticos" in data
        assert "proyectos_por_estado" in data

    def test_resumen_cuenta_proyectos_activos(self, cliente_autenticado, proyecto):
        response = cliente_autenticado.get("/api/dashboard/resumen/")
        assert response.data["total_proyectos_activos"] >= 1

    def test_resumen_incluye_indicadores_criticos(self, cliente_autenticado, indicador):
        response = cliente_autenticado.get("/api/dashboard/resumen/")
        assert len(response.data["indicadores_criticos"]) >= 1
