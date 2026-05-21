import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from dashboard.models import Proyecto, Actividad, Indicador


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="testuser",
        password="Test1234!",
    )


@pytest.fixture
def token(api_client, usuario):
    response = api_client.post(
        "/api/auth/token/",
        {"username": "testuser", "password": "Test1234!"},
        format="json",
    )
    return response.data["access"]


@pytest.fixture
def cliente_auth(api_client, token):
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
        presupuesto=500000000,
        costo_actual=100000000,
        avance_porcentaje=20.0,
        responsable=usuario,
    )


@pytest.fixture
def indicador(db, proyecto):
    return Indicador.objects.create(
        proyecto=proyecto,
        nombre="Avance fisico",
        tipo="porcentaje",
        valor_actual=15.0,
        valor_objetivo=100.0,
        umbral_critico=30.0,
    )


class TestProyectoModel:

    def test_str(self, proyecto):
        assert "Edificio Central" in str(proyecto)

    def test_dias_restantes(self, proyecto):
        assert proyecto.dias_restantes > 0

    def test_desviacion_presupuesto(self, proyecto):
        assert proyecto.desviacion_presupuesto < 0


class TestIndicadorModel:

    def test_es_critico(self, indicador):
        assert indicador.es_critico is True

    def test_rendimiento(self, indicador):
        assert indicador.rendimiento_porcentaje == 15.0


class TestActividadModel:

    def test_no_vencida(self, db, proyecto):
        actividad = Actividad.objects.create(
            proyecto=proyecto,
            nombre="Excavacion",
            fecha_vencimiento=date.today() + timedelta(days=10),
        )
        assert actividad.esta_vencida is False

    def test_vencida(self, db, proyecto):
        actividad = Actividad.objects.create(
            proyecto=proyecto,
            nombre="Cimientos",
            fecha_vencimiento=date.today() - timedelta(days=5),
        )
        assert actividad.esta_vencida is True


@pytest.mark.django_db
class TestProyectoAPI:

    def test_listar_sin_auth(self, api_client):
        response = api_client.get("/api/proyectos/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listar_con_auth(self, cliente_auth, proyecto):
        response = cliente_auth.get("/api/proyectos/")
        assert response.status_code == status.HTTP_200_OK

    def test_crear_proyecto(self, cliente_auth):
        data = {
            "nombre": "Torre Norte",
            "cliente": "Inversiones XYZ",
            "estado": "activo",
            "fecha_inicio": str(date.today()),
            "fecha_fin_estimada": str(date.today() + timedelta(days=180)),
            "presupuesto": "800000000",
            "costo_actual": "0",
            "avance_porcentaje": 0,
        }
        response = cliente_auth.post("/api/proyectos/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_actualizar_avance(self, cliente_auth, proyecto):
        response = cliente_auth.post(
            f"/api/proyectos/{proyecto.id}/actualizar-avance/",
            {"avance_porcentaje": 50},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["avance_porcentaje"] == 50


@pytest.mark.django_db
class TestDashboard:

    def test_resumen(self, cliente_auth, proyecto, indicador):
        response = cliente_auth.get("/api/dashboard/resumen/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_proyectos_activos" in response.data
        assert "top_proyectos" in response.data