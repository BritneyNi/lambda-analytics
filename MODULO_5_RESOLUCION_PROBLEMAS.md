# Módulo 5: Resolución de Problemas y Pensamiento Crítico

---

## 5.1 Caso: Optimización del Reporte que tarda 45 minutos

### 1. Métricas que recopilaría primero

| Métrica | Herramienta | Por qué importa |
|---|---|---|
| Tiempo de ejecución por fase | `time.perf_counter` + logging | Identificar dónde está el cuello de botella: ¿consulta SQL, procesamiento Python o escritura a Excel? |
| Plan de ejecución SQL | `EXPLAIN ANALYZE` en PostgreSQL | Detectar Seq Scans, joins sin índice, filas estimadas vs reales |
| CPU y RAM durante la ejecución | `top`, CloudWatch, o pg_stat_activity | Determinar si el problema es cómputo o I/O |
| Tamaño y distribución de los 500K registros | `SELECT COUNT(*), pg_size_pretty(pg_total_relation_size(...))` | Saber si es un problema de volumen real o de queries ineficientes |
| Número de queries emitidas | Django Debug Toolbar / `connection.queries` | Detectar N+1 queries |
| Tiempo de escritura a Excel | Logging alrededor de `openpyxl` / `xlsxwriter` | El export a Excel suele ser el cuello de botella más subestimado |

---

### 2. Tres causas más probables del problema de rendimiento

**Causa 1 — Consultas SQL sin optimizar (más probable)**
El reporte probablemente carga 500K filas con un `queryset.all()` o con múltiples queries N+1 (una por proyecto, una por actividad, etc.). Sin índices en columnas de filtro (fecha, estado) y sin uso de `annotate()`/`aggregate()`, PostgreSQL hace Sequential Scans sobre toda la tabla.

**Causa 2 — Procesamiento en Python fila por fila**
Si el código itera los 500K registros en Python para hacer cálculos (sumas, promedios, agrupaciones), en lugar de delegar esa lógica al motor de base de datos, el cuello de botella es CPU pura en la aplicación. Python es ~10-100x más lento que PostgreSQL para agregaciones masivas.

**Causa 3 — Escritura a Excel sin streaming**
`openpyxl` por defecto carga todo el workbook en memoria antes de escribirlo. Con 500K filas esto significa varios GB en RAM y escritura secuencial al disco, lo que puede tardar decenas de minutos por sí solo.

---

### 3. Soluciones técnicas propuestas

#### Solución A — Optimización de la consulta + cálculos en base de datos

**Implementación:**
```python
# Antes: carga todo en memoria y calcula en Python
registros = Registro.objects.filter(fecha__month=mes).all()
total = sum(r.valor for r in registros)  # itera 500K objetos

# Después: todo en una sola query con aggregate
from django.db.models import Sum, Avg, Count, F

resumen = Registro.objects.filter(
    fecha__year=año, fecha__month=mes
).select_related("proyecto").values(
    "proyecto__nombre", "proyecto__estado"
).annotate(
    total_valor=Sum("valor"),
    promedio=Avg("valor"),
    cantidad=Count("id"),
).order_by("-total_valor")

# Agregar índices en la migración:
# class Meta:
#     indexes = [models.Index(fields=["fecha", "estado"])]
```

**Pros:**
- Reducción típica de tiempo: de 45 min a 30-120 segundos.
- Sin cambios de arquitectura, se puede implementar en horas.
- El ORM de Django soporta todo esto nativamente.

**Contras:**
- Requiere conocer bien el esquema y los índices existentes.
- Cálculos muy complejos pueden ser difíciles de expresar en ORM.
- La base de datos asume más carga (aunque en PostgreSQL esto es deseable).

---

#### Solución B — Procesamiento asíncrono con Celery + streaming de Excel

**Implementación:**
```python
# tasks.py
from celery import shared_task
import xlsxwriter, io
from django.core.mail import EmailMessage

@shared_task(bind=True, max_retries=3)
def generar_reporte_diario(self, periodo, email_destino):
    try:
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"constant_memory": True})  # streaming
        worksheet = workbook.add_worksheet("Reporte")

        # Iterar con iterator() para no cargar todo en RAM
        qs = Registro.objects.filter(fecha__date=periodo).values(
            "proyecto__nombre", "valor", "estado"
        ).iterator(chunk_size=2000)

        for row_num, registro in enumerate(qs, start=1):
            worksheet.write_row(row_num, 0, [
                registro["proyecto__nombre"],
                registro["valor"],
                registro["estado"],
            ])

        workbook.close()
        output.seek(0)

        # Enviar por email
        email = EmailMessage(subject=f"Reporte {periodo}", to=[email_destino])
        email.attach(f"reporte_{periodo}.xlsx", output.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        email.send()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# Programar con Celery Beat:
# CELERY_BEAT_SCHEDULE = {
#     "reporte-diario": {
#         "task": "dashboard.tasks.generar_reporte_diario",
#         "schedule": crontab(hour=6, minute=0),
#     }
# }
```

**Pros:**
- El reporte corre en background: no bloquea el sistema durante las mañanas.
- `constant_memory=True` en xlsxwriter evita el problema de RAM con filas masivas.
- `iterator(chunk_size=2000)` procesa en lotes sin cargar 500K objetos a la vez.
- Resiliente: reintentos automáticos en caso de falla.

**Contras:**
- Requiere Celery + Redis/RabbitMQ instalados (más infraestructura).
- El reporte no está disponible "en tiempo real", sino al terminar el task.
- Más complejidad operativa: monitorear workers, colas, tareas fallidas.

---

### 4. Priorización: impacto vs tiempo de implementación

```
IMPACTO
  ↑
  │   [B - Celery Async]    ← Alta complejidad, alto impacto
  │         
  │
  │   [A - ORM + índices]   ← Baja complejidad, alto impacto  ← HACER PRIMERO
  │         
  │
  │   [Caché Redis]         ← Media complejidad, impacto moderado
  │         
  │
  └──────────────────────────────────────────→ TIEMPO DE IMPLEMENTACIÓN
    (horas)              (días)            (semanas)
```

**Recomendación:** Implementar primero la Solución A (ORM + índices). Es un cambio de pocas horas que puede reducir el tiempo de 45 min a 1-2 min. Si con eso no es suficiente o si el negocio necesita que el reporte no bloquee el sistema, agregar entonces la Solución B (Celery).

---

### 5. Medidas preventivas

1. **Monitoreo de queries lentas:** Configurar `pg_stat_statements` en PostgreSQL para alertar sobre queries > 5s. Agregar `django-silk` o Datadog APM en staging.

2. **Tests de rendimiento en CI:** Agregar un test que mida el tiempo de generación del reporte con un dataset representativo (ej. 10K filas) y falle si supera un umbral. Evita regresiones de performance silenciosas.

3. **Paginación en exportaciones masivas:** Nunca exportar más de N registros en una sola operación síncrona. Implementar exportaciones paginadas o divididas por rango de fechas.

4. **Revisión de índices en cada migración:** Política de equipo: toda migración que agrega una columna usada en `filter()`, `order_by()` o `join()` debe agregar el índice correspondiente.

5. **SLOs para reportes:** Definir un SLO (Service Level Objective) explícito: "El reporte diario debe completarse en < 5 min". Monitorearlo en CloudWatch o Grafana con alertas automáticas.

---

## 5.2 Pregunta de Diseño: Sistema de Reportes Automatizados

### Arquitectura de alto nivel

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                       │
│  Report Builder UI │ Scheduler UI │ Dashboard de reportes │
└──────────────────────────┬───────────────────────────────┘
                           │ REST API / WebSocket
┌─────────────────────────────────────────────────────────┐
│                  API GATEWAY (Django + DRF)               │
│   /reports  │  /datasources  │  /schedules  │  /jobs      │
└──┬──────────┬───────────────┬───────────────┬────────────┘
   │          │               │               │
┌──▼──┐  ┌───▼────┐  ┌───────▼───┐  ┌────────▼──────────┐
│     │  │        │  │           │  │                    │
│ DB  │  │Connector│  │ Scheduler │  │  Worker Pool       │
│Repo │  │Registry │  │ (Celery   │  │  (Celery Workers)  │
│     │  │         │  │  Beat)    │  │  - Extrae datos    │
│Posg.│  │Adapters:│  │           │  │  - Calcula KPIs    │
│     │  │- SQL    │  │           │  │  - Genera Excel/   │
│     │  │- REST   │  │           │  │    PDF/CSV         │
│     │  │- CSV    │  │           │  │  - Envía email     │
└─────┘  └────────┘  └───────────┘  └────────────────────┘
                                              │
                                     ┌────────▼──────────┐
                                     │   S3 / Storage     │
                                     │  (archivos output) │
                                     └───────────────────┘
```

---

### Componentes principales y responsabilidades

**1. Report Builder (Frontend)**
Interfaz drag-and-drop donde el usuario no técnico selecciona fuente de datos, columnas, filtros y tipo de visualización. Genera una configuración JSON serializada.

**2. Connector Registry (Backend)**
Catálogo de adaptadores para conectar fuentes heterogéneas: bases de datos SQL (via SQLAlchemy), APIs REST, archivos CSV/Excel en S3. Cada conector expone una interfaz uniforme `fetch(config) → DataFrame`.

**3. Report Engine (Worker Pool)**
Workers de Celery que reciben un job, llaman al conector adecuado, aplican transformaciones (filtros, agrupaciones, fórmulas), y generan el output en el formato solicitado (Excel con xlsxwriter, PDF con WeasyPrint, CSV nativo).

**4. Scheduler**
Celery Beat con persistencia en PostgreSQL (django-celery-beat). Permite cron expressions configuradas por el usuario desde la UI: "todos los lunes a las 7am".

**5. Notification Service**
Microservicio ligero que envía los reportes generados por email (SendGrid/SES) con el archivo adjunto y un link a S3.

---

### Tecnologías y justificación

| Tecnología | Rol | Por qué |
|---|---|---|
| Django + DRF | API y configuración de reportes | Ecosistema maduro, ORM potente, admin gratis |
| Celery + Redis | Cola de tareas y scheduler | Estándar de facto en Python para jobs asincrónicos |
| SQLAlchemy | Capa de conectores SQL | Soporta 20+ bases de datos con interfaz uniforme |
| pandas | Transformaciones de datos | API expresiva para filtros/agrupaciones/fórmulas sobre DataFrames |
| xlsxwriter / WeasyPrint | Generación de Excel / PDF | xlsxwriter: streaming, alto rendimiento; WeasyPrint: HTML→PDF con CSS |
| S3 | Almacenamiento de outputs | Económico, durable, presigned URLs para descarga segura |
| PostgreSQL | Configuraciones y auditoría | ACID, JSONB para configuraciones flexibles de reportes |
| React + react-query | Frontend | SPA con manejo de estado asíncrono y caché |

---

### Consideraciones de seguridad

1. **Aislamiento de conectores:** Cada conector corre con credenciales de solo lectura. Las credenciales se almacenan en AWS Secrets Manager (nunca en DB).

2. **Sandboxing de queries custom:** Si el usuario puede escribir SQL libre, ejecutarlo en una conexión con `statement_timeout = 30s` y `SET ROLE readonly_role` para prevenir DROP/UPDATE.

3. **Autorización por reporte:** RBAC (Role-Based Access Control): un usuario solo puede ver y ejecutar reportes de su organización (multitenancy con `org_id` en cada modelo).

4. **Validación de parámetros:** Todo input del usuario que llegue a un conector debe ser sanitizado. Usar queries parametrizadas; nunca interpolación de strings en SQL.

5. **Rate limiting:** Limitar jobs simultáneos por organización para evitar que un cliente sature los workers y afecte a otros.

---

### Garantías de escalabilidad

- **Horizontal:** Los workers de Celery son stateless; se escalan simplemente añadiendo contenedores. En AWS: ECS Auto Scaling basado en profundidad de la cola SQS/Redis.

- **Reportes pesados:** Si un reporte supera un umbral de filas (ej. > 100K), automáticamente se genera en modo streaming y se entrega por S3 + email en lugar de descarga directa.

- **Multitenancy:** Colas separadas por tenant priority tier (premium vs standard), garantizando SLAs diferenciados sin modificar código.

- **Caché de resultados:** Reportes idénticos ejecutados en la misma ventana horaria devuelven el resultado cacheado en Redis, reduciendo carga en base de datos.
