# DigiKawsay - Phase 8 Hardening - Test Plan

## Testing Protocol
DO NOT EDIT THIS SECTION

## Incorporate User Feedback
- Previous testing identified login form submission issues in browser automation
- Backend APIs work correctly via curl

## Phase 8: Hardening Features to Test

### Backend Security Features

backend:
  - task: "Rate Limiting"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    priority: "high"
    needs_retesting: true
    test_method: "Try 12+ login attempts rapidly, verify 429 response after limit"

  - task: "Brute Force Protection"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    priority: "high"
    needs_retesting: true
    test_method: "5 failed logins should lock account for 15 minutes"

  - task: "Security Config Endpoint"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    endpoint: "GET /api/auth/security/config"
    priority: "high"
    needs_retesting: true
    test_method: "Admin/security_officer can view security settings"

  - task: "Locked Accounts Endpoint"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    endpoint: "GET /api/auth/security/locked-accounts"
    priority: "high"
    needs_retesting: true

  - task: "Unlock Account Endpoint"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    endpoint: "POST /api/auth/security/unlock-account/{email}"
    priority: "high"
    needs_retesting: true

  - task: "Session Timeout"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    priority: "high"
    needs_retesting: true
    test_method: "30 min inactivity timeout implemented in get_current_user"

  - task: "MongoDB Indexes"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "43 indexes created on startup for performance optimization"

  - task: "Persistent Login Attempts"
    implemented: true
    working: null
    file: "/app/backend/server.py"
    priority: "medium"
    needs_retesting: true
    test_method: "Login attempts stored in MongoDB with TTL (30 days)"

frontend:
  - task: "Login Flow"
    implemented: true
    working: null
    file: "/app/frontend/src/pages/LoginPage.jsx"
    priority: "high"
    needs_retesting: true
    test_method: "Test login with admin@test.com / test123"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 9
  phase: "8 - Hardening"

test_plan:
  current_focus:
    - "Security endpoints (config, locked-accounts, unlock)"
    - "Rate limiting and brute force protection"
    - "Session timeout behavior"
    - "Login flow in browser"
  credentials:
    admin:
      email: "admin@test.com"
      password: "test123"
    participant:
      email: "participante@test.com"
      password: "test123"
