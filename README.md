# Lambda Analytics — Dashboard Analítico

Solución completa para la Prueba Técnica de Desarrollador Web Semi-Senior.
Stack: **Python 3.11 + Django 4.2 · React 18 + Recharts · PostgreSQL · Redis · Docker · AWS ECS**

---

## Estructura del proyecto

```
lambda_dashboard/
├── backend/
│   ├── models.py          # Proyecto, Actividad, Indicador, Reporte
│   ├── serializers.py     # Serializers con validaciones de negocio
│   ├── views.py           # ViewSets + DashboardViewSet (GET /api/dashboard/resumen/)
│   ├── urls.py            # Router DRF + JWT endpoints
│   ├── tests.py           # 20+ tests con pytest (cobertura > 80%)
│   ├── settings.py        # Configuración Django
│   └── requirements.txt
├── frontend/
│   ├── useProyectos.js    # Custom hooks: useProyectos + useDashboardResumen
│   ├── Dashboard.jsx      # Componente principal con KPIs, tabla y gráfico
│   └── Dashboard.test.jsx # Tests con React Testing Library + MSW
├── infra/
│   ├── Dockerfile         # Multi-stage build optimizado
│   ├── docker-compose.yml # web + db (PostgreSQL) + redis + nginx + worker
│   └── ci-cd.yml          # GitHub Actions: test → build ECR → deploy ECS
└── MODULO_5_RESOLUCION_PROBLEMAS.md
```

---

## Instalación y ejecución

### Requisitos
- Python 3.11+
- Node.js 18+
- Docker Desktop

### Con Docker (recomendado)

```bash
# 1. Copiar variables de entorno
cp infra/.env.example infra/.env
# Editar infra/.env con tus valores

# 2. Levantar todos los servicios
cd infra
docker compose up --build

# 3. Aplicar migraciones y crear superusuario
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Accesos:
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Docs (Swagger): http://localhost:8000/api/schema/swagger-ui/
- Frontend: http://localhost:3000

### Desarrollo local (sin Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export DB_HOST=localhost DB_NAME=lambda_dashboard DB_USER=postgres DB_PASSWORD=postgres
export REDIS_URL=redis://localhost:6379/0
export DJANGO_SECRET_KEY=dev-secret DEBUG=True

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend (en otra terminal)
cd frontend
npm install
npm start
```

---

## Endpoints principales

### Autenticación JWT

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/token/` | Obtener access + refresh token |
| POST | `/api/auth/token/refresh/` | Renovar access token |

### Recursos

| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/proyectos/` | Listar (filtros, búsqueda, paginación) / Crear |
| GET/PUT/PATCH/DELETE | `/api/proyectos/{id}/` | Detalle con actividades, indicadores y reportes |
| POST | `/api/proyectos/{id}/actualizar-avance/` | Actualizar % avance |
| GET | `/api/proyectos/{id}/resumen/` | KPIs del proyecto |
| GET | `/api/dashboard/resumen/` | **Resumen global del dashboard** |
| GET/POST | `/api/actividades/` | Filtros: proyecto, estado, prioridad, vencidas |
| GET/POST | `/api/indicadores/` | Filtro: `?criticos=true` para solo críticos |
| GET/POST | `/api/reportes/` | Filtros: proyecto, tipo |

### Parámetros de filtrado para `/api/proyectos/`

```
?estado=activo                 # activo | pausado | completado | cancelado
?search=torre                  # busca en nombre, descripción y cliente
?ordering=-avance_porcentaje   # ordenar (- para descendente)
?avance_min=50&avance_max=90   # rango de avance
?page=2&page_size=10           # paginación
```

---

## Ejecutar tests

```bash
# Backend
cd backend
pytest --cov=dashboard --cov-report=term-missing -v
# Cobertura mínima: 80%

# Frontend
cd frontend
npm test -- --coverage --watchAll=false
```

---

## Arquitectura AWS

```
Internet
    │
    ▼
[CloudFront CDN]──── S3 (assets React)
    │
    ▼
[Application Load Balancer]
    │         │
    ▼         ▼
[ECS Task] [ECS Task]   ← Auto Scaling (2-10 instancias)
 Django      Django
    │
    ├──► [RDS PostgreSQL Multi-AZ]   ← Primary + Standby en 2 AZs
    ├──► [ElastiCache Redis]         ← Caché y cola Celery
    └──► [S3 Reportes/Media]         ← Archivos generados
         
[ECS Task — Celery Worker]          ← Procesa reportes asincrónicos
    │
    └──► [SES / SendGrid]            ← Envío de emails

Seguridad:
- VPC privada: RDS y Redis sin acceso público
- Security Groups: solo ECS puede hablar con RDS (puerto 5432)
- Secrets Manager: credenciales de DB y JWT secret
- WAF en CloudFront: protección contra SQL injection / DDoS
- IAM Roles: ECS Tasks con permisos mínimos necesarios
```

---

## Decisiones de arquitectura

**¿Por qué DRF con ViewSets en lugar de APIView?**
Los ViewSets con `DefaultRouter` generan automáticamente los 5 endpoints REST estándar y las URLs correspondientes. Reduce boilerplate y mantiene consistencia. Las `@action` personalizadas permiten extender sin romper la convención.

**¿Por qué JWT con simplejwt?**
Es stateless (no requiere tabla de sesiones), se puede verificar en cualquier servicio sin consultar la DB, y tiene rotación de refresh tokens configurable. Para un dashboard analítico con potencial de múltiples microservicios es la mejor opción.

**¿Por qué `select_related` + `annotate` en lugar de serializers anidados?**
Los serializers anidados generan N+1 queries por defecto. Al anotar `total_actividades` y `actividades_completadas` en el queryset, se resuelve con una sola query SQL usando JOINs, independientemente del número de proyectos en el listado.

**¿Por qué custom hook con caché en memoria en el frontend?**
Para evitar llamadas repetidas a la API cuando el usuario navega entre vistas. El TTL de 60s garantiza datos frescos sin sacrificar UX. `AbortController` cancela requests en vuelo cuando cambian los filtros, evitando race conditions.

**¿Por qué multi-stage Dockerfile?**
La etapa `deps` instala `gcc` y compila psycopg2. La etapa `runtime` solo copia los binarios ya compilados, sin herramientas de build. Resultado: imagen final ~60% más pequeña y sin superficie de ataque innecesaria.
