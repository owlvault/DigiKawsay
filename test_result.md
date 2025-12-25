# Testing Data for Phase 6: RunaData

user_problem_statement: "DigiKawsay - Phase 6: RunaData - Gobernanza de Datos con RBAC/ABAC, control dual y archivado"

backend:
  - task: "RBAC Permissions API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/governance/permissions returns 27 permissions for admin role"

  - task: "Data Policies API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST/GET/PUT /api/governance/policies endpoints working"

  - task: "Dual Approval Workflow"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Dual approval requires admin + security_officer. Endpoints working."

  - task: "Data Archival API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST /api/governance/archive/run and GET /api/governance/archive/records working"

  - task: "Governance Metrics"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/governance/metrics returns compliance score 80%"

frontend:
  - task: "GovernancePage"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/GovernancePage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Page loads with dashboard, metrics cards, tabs for policies/approvals/archive/permissions"

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
        comment: "Route /governance added. Navigation link enabled in Layout.jsx for admin/data_steward/security_officer"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 7
  run_ui: true

test_plan:
  current_focus:
    - "GovernancePage - verify dashboard, metrics, tabs"
    - "Data Policies - create and list policies"
    - "Dual Approval - test approval workflow"
    - "Permissions API - verify role permissions"
  stuck_tasks: []
  test_all: true

credentials:
  admin:
    email: "admin@test.com"
    password: "test123"
