# Testing Data for Phase 5: RunaFlow

user_problem_statement: "DigiKawsay - Phase 5: RunaFlow - Gestión de Iniciativas y Rituales Organizacionales"

backend:
  - task: "Initiatives CRUD API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST/GET/PUT/DELETE /api/initiatives/ endpoints working - tested with curl"

  - task: "Initiative Scoring (ICE/RICE)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "ICE and RICE scoring calculations working - final_score calculated on create/update"

  - task: "Rituals CRUD API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST/GET/PUT/DELETE /api/rituals/ endpoints implemented"

  - task: "Initiative Stats API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/initiatives/stats/{campaign_id} returns stats with top_contributors"

frontend:
  - task: "RunaFlow Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/RunaFlowPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Page loads with Kanban view, stats, create/edit dialog. SelectItem fix applied."

  - task: "Rituals Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/RitualsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Page loads with ritual cards, create/edit dialog. SelectItem fix applied."

  - task: "Navigation and Routes"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Routes /roadmap and /rituals added. Navigation links enabled in Layout.jsx"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 6
  run_ui: true

test_plan:
  current_focus:
    - "RunaFlow Page - verify Kanban view, create initiative, scoring"
    - "Rituals Page - verify create ritual dialog and list"
    - "Backend APIs - verify all Phase 5 endpoints"
  stuck_tasks: []
  test_all: true

credentials:
  admin:
    email: "admin@test.com"
    password: "test123"
