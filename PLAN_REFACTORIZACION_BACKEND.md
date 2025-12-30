# 🏗️ PLAN DE REFACTORIZACIÓN DEL BACKEND - DIGIKAWSAY

## 📋 Resumen Ejecutivo

**Estado Actual:**
- Archivo monolítico: `server.py` con **5,331 líneas**
- 75 modelos Pydantic
- 11 servicios de negocio
- 22 routers con 117 endpoints
- 33 imports externos

**Objetivo:**
Transformar el backend monolítico en una arquitectura modular, mantenible y escalable.

---

## 📁 ESTRUCTURA PROPUESTA

```
/app/backend/
├── server.py                    # Entry point (reducido a ~100 líneas)
├── requirements.txt
├── .env
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app configuration
│   ├── config.py                # Settings & environment variables
│   ├── database.py              # MongoDB connection & helpers
│   │
│   ├── models/                  # Pydantic Models
│   │   ├── __init__.py
│   │   ├── base.py              # TimestampMixin, base models
│   │   ├── auth.py              # User, Token, Login models
│   │   ├── campaign.py          # Campaign, Script, Segment models
│   │   ├── chat.py              # Session, Message, Transcript models
│   │   ├── insight.py           # Insight, Taxonomy models
│   │   ├── compliance.py        # Audit, Consent, PII models
│   │   ├── network.py           # NetworkNode, NetworkEdge, Snapshot models
│   │   ├── initiative.py        # Initiative, Ritual models
│   │   ├── governance.py        # AccessPolicy, DataPolicy models
│   │   └── observability.py     # Metrics, Health models
│   │
│   ├── services/                # Business Logic
│   │   ├── __init__.py
│   │   ├── audit_service.py     # AuditService
│   │   ├── pii_service.py       # PIIVaultService, PseudonymizationService
│   │   ├── chat_service.py      # VALChatService
│   │   ├── insight_service.py   # InsightExtractionService
│   │   ├── network_service.py   # NetworkAnalysisService
│   │   ├── initiative_service.py # InitiativeService, RitualService
│   │   ├── governance_service.py # GovernanceService
│   │   └── observability_service.py # ObservabilityService
│   │
│   ├── routes/                  # API Endpoints
│   │   ├── __init__.py
│   │   ├── auth.py              # /api/auth/* (6 endpoints)
│   │   ├── users.py             # /api/users/* (5 endpoints)
│   │   ├── tenants.py           # /api/tenants/* (2 endpoints)
│   │   ├── campaigns.py         # /api/campaigns/* (6 endpoints)
│   │   ├── scripts.py           # /api/scripts/* (5 endpoints)
│   │   ├── sessions.py          # /api/sessions/*, /api/chat/* (5 endpoints)
│   │   ├── insights.py          # /api/insights/*, /api/taxonomy/* (11 endpoints)
│   │   ├── compliance.py        # /api/audit/*, /api/privacy/*, /api/consent/* (16 endpoints)
│   │   ├── network.py           # /api/network/* (9 endpoints)
│   │   ├── initiatives.py       # /api/initiatives/*, /api/rituals/* (16 endpoints)
│   │   ├── governance.py        # /api/governance/* (15 endpoints)
│   │   └── observability.py     # /api/observability/* (12 endpoints)
│   │
│   ├── middleware/              # Custom Middleware
│   │   ├── __init__.py
│   │   ├── security.py          # SecurityHeadersMiddleware, PIISanitizer
│   │   ├── rate_limit.py        # Rate limiting configuration
│   │   ├── correlation.py       # CorrelationIdMiddleware
│   │   └── logging.py           # ObservabilityMiddleware, StructuredLogger
│   │
│   ├── utils/                   # Utilities
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT, password hashing
│   │   ├── validators.py        # Password validation, email checks
│   │   ├── serializers.py       # MongoDB serialization
│   │   └── constants.py         # Enums, constants
│   │
│   └── core/                    # Core Dependencies
│       ├── __init__.py
│       ├── dependencies.py      # get_current_user, get_db
│       └── exceptions.py        # Custom exceptions
│
└── tests/                       # Unit & Integration Tests
    ├── __init__.py
    ├── conftest.py              # Pytest fixtures
    ├── test_auth.py
    ├── test_campaigns.py
    ├── test_chat.py
    ├── test_insights.py
    ├── test_network.py
    ├── test_initiatives.py
    ├── test_governance.py
    └── test_observability.py
```

---

## 📅 PLAN DE EJECUCIÓN (5 Sprints)

### Sprint 1: Infraestructura Base (2-3 días) ✅ COMPLETADO
**Objetivo:** Crear estructura de carpetas y configuración base

| Tarea | Archivo | Prioridad |
|-------|---------|-----------|
| Crear estructura de carpetas | `/app/backend/app/` | P0 |
| Extraer configuración | `app/config.py` | P0 |
| Extraer conexión DB | `app/database.py` | P0 |
| Crear módulo de utilidades | `app/utils/` | P0 |
| Crear dependencies | `app/core/dependencies.py` | P0 |

**Entregable:** Backend arranca con nueva estructura, `server.py` importa desde módulos.

---

### Sprint 2: Modelos Pydantic (2 días) ✅ COMPLETADO
**Objetivo:** Separar todos los modelos en archivos dedicados

| Archivo Destino | Modelos | Líneas Est. |
|-----------------|---------|-------------|
| `models/base.py` | TimestampMixin, BaseResponse | ~50 |
| `models/auth.py` | User, UserCreate, UserLogin, Token, etc. | ~100 |
| `models/campaign.py` | Campaign, Script, Segment, Invite | ~150 |
| `models/chat.py` | Session, Message, Transcript | ~100 |
| `models/insight.py` | Insight, TaxonomyCategory, Validation | ~100 |
| `models/compliance.py` | AuditLog, Consent, PIIRecord, ReidentificationRequest | ~150 |
| `models/network.py` | NetworkNode, NetworkEdge, NetworkSnapshot, Metrics | ~100 |
| `models/initiative.py` | Initiative, Ritual, Comment | ~150 |
| `models/governance.py` | AccessPolicy, DataPolicy, Permission | ~200 |
| `models/observability.py` | HealthCheck, SystemMetrics, LogEntry | ~100 |

**Entregable:** Todos los modelos en archivos separados, imports funcionando.

---

### Sprint 3: Servicios de Negocio (3 días) ✅ COMPLETADO
**Objetivo:** Extraer lógica de negocio a servicios independientes
**Fecha de completación:** 2025-12-29

| Servicio | Archivo Destino | Líneas Est. | Complejidad |
|----------|-----------------|-------------|-------------|
| AuditService | `services/audit_service.py` | ~80 | Baja |
| PIIVaultService | `services/pii_service.py` | ~150 | Media |
| PseudonymizationService | `services/pii_service.py` | (incluido) | Media |
| SuppressionService | `services/pii_service.py` | (incluido) | Media |
| VALChatService | `services/chat_service.py` | ~100 | Alta |
| InsightExtractionService | `services/insight_service.py` | ~120 | Alta |
| NetworkAnalysisService | `services/network_service.py` | ~400 | Alta |
| InitiativeService | `services/initiative_service.py` | ~150 | Media |
| RitualService | `services/initiative_service.py` | (incluido) | Media |
| GovernanceService | `services/governance_service.py` | ~250 | Alta |
| ObservabilityService | `services/observability_service.py` | ~300 | Media |

**Entregable:** Servicios desacoplados, inyección de dependencias funcional.

---

### Sprint 4: Rutas API (3-4 días) ✅ COMPLETADO
**Objetivo:** Separar endpoints en routers modulares
**Fecha de completación:** 2025-12-30

| Router | Archivo Destino | Estado |
|--------|-----------------|--------|
| auth | `api/auth.py` | ✅ |
| users | `api/users.py` | ✅ |
| tenants | `api/tenants.py` | ✅ |
| campaigns | `api/campaigns.py` | ✅ |
| scripts | `api/scripts.py` | ✅ |
| sessions, chat | `api/sessions.py` | ✅ |
| insights | `api/insights.py` | ✅ |
| taxonomy | `api/taxonomy.py` | ✅ |
| audit, privacy, transcripts | `api/audit.py` | ✅ |
| consent | `api/consent.py` | ✅ |
| network | `api/network.py` | ✅ |
| initiatives, rituals | `api/initiatives.py` | ✅ |
| governance, reidentification | `api/governance.py` | ✅ |
| observability | `api/observability.py` | ✅ |
| segments, invites | `api/segments.py` | ✅ |

**Total:** 16 archivos, 2,781 líneas, 102 rutas registradas

**Entregable:** Todos los endpoints migrados, API 100% funcional.

---

### Sprint 5: Middleware y Cleanup (2 días)
**Objetivo:** Extraer middleware, limpiar y documentar

| Tarea | Archivo | Prioridad |
|-------|---------|-----------|
| SecurityHeadersMiddleware | `middleware/security.py` | P0 |
| Rate limiting | `middleware/rate_limit.py` | P0 |
| CorrelationIdMiddleware | `middleware/correlation.py` | P1 |
| ObservabilityMiddleware | `middleware/logging.py` | P1 |
| StructuredLogger | `middleware/logging.py` | P1 |
| PIISanitizer | `middleware/security.py` | P1 |
| Documentación OpenAPI | Decoradores en routes | P2 |
| Limpieza server.py | Reducir a ~100 líneas | P0 |

**Entregable:** Backend completamente modularizado, `server.py` solo como entry point.

---

## 🔄 ESTRATEGIA DE MIGRACIÓN

### Enfoque: Strangler Fig Pattern (Incremental)

```
Fase 1: Crear módulos vacíos
         ↓
Fase 2: Copiar código a módulos (sin eliminar original)
         ↓
Fase 3: Cambiar imports en server.py para usar módulos
         ↓
Fase 4: Verificar funcionamiento con tests
         ↓
Fase 5: Eliminar código duplicado de server.py
         ↓
Fase 6: Repetir para siguiente componente
```

### Orden de Migración Recomendado

1. **config.py** → Sin dependencias, base para todo
2. **database.py** → Solo depende de config
3. **models/** → Solo dependen de config
4. **utils/** → Solo dependen de models
5. **services/** → Dependen de models, utils, database
6. **middleware/** → Dependen de services
7. **routes/** → Dependen de todo lo anterior
8. **server.py** → Solo importa y configura

---

## ✅ CHECKLIST DE VALIDACIÓN

### Por cada componente migrado:

- [ ] El código compila sin errores
- [ ] Los imports son correctos (sin circulares)
- [ ] Los tests pasan (si existen)
- [ ] El endpoint responde correctamente
- [ ] Los logs se generan correctamente
- [ ] No hay regresiones en funcionalidad

### Validación Final:

- [ ] `server.py` tiene menos de 150 líneas
- [ ] Todos los endpoints funcionan (117 endpoints)
- [ ] Rate limiting funciona
- [ ] Autenticación funciona
- [ ] Base de datos conecta correctamente
- [ ] Logs estructurados funcionan
- [ ] Métricas de observabilidad funcionan

---

## 📊 MÉTRICAS DE ÉXITO

| Métrica | Antes | Después | Objetivo |
|---------|-------|---------|----------|
| Líneas en server.py | 5,331 | <150 | ✅ |
| Archivos Python | 1 | ~35 | ✅ |
| Tamaño promedio archivo | 5,331 | <200 | ✅ |
| Tiempo de comprensión | Alto | Bajo | ✅ |
| Facilidad de testing | Difícil | Fácil | ✅ |
| Riesgo de conflictos Git | Alto | Bajo | ✅ |

---

## ⚠️ RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Imports circulares | Alta | Medio | Usar TYPE_CHECKING, lazy imports |
| Regresiones funcionales | Media | Alto | Tests antes de cada cambio |
| Downtime durante migración | Baja | Alto | Migración incremental, feature flags |
| Pérdida de datos | Baja | Crítico | Backup antes de cada sprint |

---

## 🛠️ HERRAMIENTAS RECOMENDADAS

- **Linting:** `ruff` (ya configurado)
- **Formatting:** `black`
- **Type checking:** `mypy`
- **Testing:** `pytest` + `pytest-asyncio`
- **Coverage:** `pytest-cov`

---

## 📝 EJEMPLO DE CÓDIGO REFACTORIZADO

### Antes (server.py monolítico):
```python
# server.py - 5,331 líneas
from fastapi import FastAPI, APIRouter, HTTPException, Depends
# ... 30+ imports ...

app = FastAPI()

# ... 75 modelos Pydantic ...
# ... 11 servicios ...
# ... 22 routers ...
# ... 117 endpoints ...
```

### Después (estructura modular):
```python
# server.py - ~100 líneas
from app.main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

```python
# app/main.py
from fastapi import FastAPI
from app.config import settings
from app.database import init_db
from app.routes import (
    auth_router, users_router, campaigns_router,
    insights_router, network_router, governance_router,
    observability_router
)
from app.middleware import setup_middleware

def create_app() -> FastAPI:
    app = FastAPI(
        title="DigiKawsay API",
        version="1.0.0",
        description="Plataforma de Facilitación PAR"
    )
    
    setup_middleware(app)
    
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(users_router, prefix="/api/users", tags=["Users"])
    # ... otros routers ...
    
    @app.on_event("startup")
    async def startup():
        await init_db()
    
    return app
```

---

## 📅 CRONOGRAMA ESTIMADO

| Sprint | Duración | Fechas Est. |
|--------|----------|-------------|
| Sprint 1: Infraestructura | 2-3 días | Día 1-3 |
| Sprint 2: Modelos | 2 días | Día 4-5 |
| Sprint 3: Servicios | 3 días | Día 6-8 |
| Sprint 4: Rutas | 3-4 días | Día 9-12 |
| Sprint 5: Middleware | 2 días | Día 13-14 |
| **TOTAL** | **~14 días** | **2-3 semanas** |

---

## 🎯 PRÓXIMOS PASOS

1. **Aprobar este plan** con stakeholders
2. **Crear branch** `refactor/modular-backend`
3. **Ejecutar Sprint 1** - Infraestructura base
4. **Validar** funcionamiento después de cada sprint
5. **Merge** a main cuando esté completo

---

*Plan generado para DigiKawsay v0.8.0 → v1.0.0*
