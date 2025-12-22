# DigiKawsay - Requirements & Architecture

## 📋 Problema Original
DigiKawsay es una plataforma de facilitación conversacional con VAL, un chatbot entrenado para campañas de facilitación de entrevistas con habilidades de coach ontológico y facilitador de procesos de Investigación Acción Participativa (IAP).

## ✅ FASE 1 - Completada

### Backend (FastAPI + MongoDB)
- **Autenticación**: JWT con roles (admin, facilitator, analyst, participant, sponsor)
- **Multi-tenancy**: Soporte para múltiples organizaciones
- **Campañas**: CRUD completo con estados (draft, active, paused, closed)
- **Consentimiento**: Sistema de consentimiento informado antes de participar
- **Sesiones**: Gestión de sesiones de diálogo
- **VAL Chat**: Integración con Gemini Flash para facilitación conversacional
- **Transcripciones**: Captura y almacenamiento de conversaciones
- **Dashboard Stats**: Métricas para administradores

### Frontend (React + Zustand)
- **Login/Register**: Sistema completo con selección de rol
- **Dashboard**: Vista de métricas y campañas activas
- **Campañas**: Lista, creación y gestión
- **Chat VAL**: Interfaz conversacional con el facilitador IA
- **Consentimiento**: Modal de aceptación antes de participar
- **Layout**: Navegación sidebar con rutas protegidas

## ✅ FASE 2 - Completada

### Backend - Nuevas funcionalidades
- **Scripts (Guiones)**: CRUD completo con pasos/preguntas estructuradas
- **Versionamiento**: Historial de versiones automático al editar guiones
- **Duplicación**: Clonar guiones existentes
- **Segmentos**: Modelo para segmentación de participantes
- **Invitaciones**: Sistema individual y bulk para invitar participantes
- **Cobertura**: Endpoint /campaigns/{id}/coverage con métricas de participación
- **Actualización de campañas**: PUT para editar toda la configuración

### Frontend - Nuevas páginas
- **Guiones** (/scripts): Lista de guiones con búsqueda y acciones rápidas
- **Editor de Guiones** (/scripts/new, /scripts/:id): Crear/editar con pasos drag-and-drop
- **Detalle de Campaña** (/campaigns/:id): Vista completa con tabs
  - Tab Configuración: Editar nombre, objetivo, guión asociado, meta
  - Tab Invitaciones: Enviar y listar invitaciones
- **Cobertura**: Visualización de tasas de participación y completitud

## ✅ FASE 3 - Completada

### Backend - Nuevas funcionalidades
- **Insights (Hallazgos)**: CRUD completo con tipos (tema, tensión, símbolo, oportunidad, riesgo)
- **Extracción IA**: Extracción automática de insights desde transcripciones usando Gemini Flash
- **Pseudonimización**: Servicio para anonimizar transcripciones (emails, teléfonos, nombres)
- **Taxonomía**: Categorías configurables para clasificar hallazgos
- **Member-checking**: Sistema de validación participativa de insights
- **Stats de Insights**: Endpoint con métricas por tipo, estado, sentimiento

### Frontend - Nuevas páginas
- **Insights Workbench** (/insights/:campaignId): Panel de hallazgos con filtros y validación
- **Crear Insight** (/insights/:campaignId/new): Formulario para agregar hallazgos manuales
- **Taxonomía** (/taxonomy): Gestión de categorías con colores y tipos

## 🔄 FASES PENDIENTES

### FASE 4 - RunaMap (SNA)
- [ ] Construcción de grafo de red social
- [ ] Snapshots y métricas de red (densidad, betweenness, comunidades)
- [ ] Visualización interactiva con react-force-graph-2d
- [ ] Identificación de brokers e influenciadores

### FASE 5 - RunaFlow y RunaData
- [ ] Backlog de iniciativas desde hallazgos
- [ ] Scoring y priorización de iniciativas
- [ ] Gestión de rituales organizacionales
- [ ] Políticas de datos versionadas
- [ ] Catálogo de datos y linaje
- [ ] Auditoría completa (RBAC/ABAC)
- [ ] Exportaciones PDF y CSV

## 🔧 Stack Tecnológico
- **Backend**: FastAPI + MongoDB + emergentintegrations
- **Frontend**: React 19 + Zustand + Shadcn/UI + Tailwind
- **IA**: Gemini 3 Flash (via Emergent LLM Key)
- **Visualización**: react-force-graph-2d, Recharts

## 🔑 Credenciales de Prueba
- Admin: admin@test.com / test123
- Facilitador: demo@digikawsay.com / demo123
