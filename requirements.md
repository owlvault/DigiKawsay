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

### Diseño
- Corporativo profesional en tonos azul (Slate 900) y naranja (Orange 500)
- Tipografía: Outfit (headings) + Inter (body)
- Componentes Shadcn/UI

## 🔄 FASES PENDIENTES

### FASE 2 - Campañas y Guiones
- [ ] Editor de guiones conversacionales
- [ ] Versionamiento de scripts
- [ ] Invitaciones y segmentos de participantes
- [ ] Monitoreo de cobertura por segmento

### FASE 3 - Pipeline y RunaCultur
- [ ] Pseudonimización/anonimización de transcripciones
- [ ] Extracción de insights con IA
- [ ] Panel de hallazgos (Insights Workbench)
- [ ] Taxonomía configurable (temas, tensiones, símbolos)
- [ ] Flujo de validación participativa (member-checking)

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
