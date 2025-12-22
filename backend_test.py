#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class DigiKawsayAPITester:
    def __init__(self, base_url="https://val-ontological-chat.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.campaigns = {}
        self.sessions = {}
        self.consents = {}
        self.scripts = {}
        self.invites = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", error=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {error}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "error": error
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if token:
            test_headers['Authorization'] = f'Bearer {token}'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                print(f"   ✅ Status: {response.status_code}")
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json().get('detail', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                print(f"   ❌ {error_msg}")
                self.log_test(name, False, error=error_msg)
                return False, {}

        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"   ❌ {error_msg}")
            self.log_test(name, False, error=error_msg)
            return False, {}

    def test_health_check(self):
        """Test API health"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )
        return success

    def test_user_registration(self, role="participant"):
        """Test user registration"""
        timestamp = int(time.time())
        user_data = {
            "email": f"test_{role}_{timestamp}@test.com",
            "password": "test123",
            "full_name": f"Test {role.title()} {timestamp}",
            "role": role
        }
        
        success, response = self.run_test(
            f"Register {role.title()} User",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'access_token' in response:
            self.tokens[role] = response['access_token']
            self.users[role] = response['user']
            return True, response
        return False, {}

    def test_user_login(self, role="participant"):
        """Test user login with existing credentials"""
        # Try with provided test credentials first
        if role == "admin":
            login_data = {"email": "admin@test.com", "password": "test123"}
        else:
            login_data = {"email": "participant@test.com", "password": "test123"}
        
        success, response = self.run_test(
            f"Login {role.title()} User",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.tokens[role] = response['access_token']
            self.users[role] = response['user']
            return True, response
        
        # If hardcoded credentials failed, skip login test for this role
        print(f"   ⚠️  Skipping login test for {role} - using registered user token")
        return False, {}

    def test_get_current_user(self, role="participant"):
        """Test get current user info"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"Get Current User ({role})",
            "GET",
            "auth/me",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_create_campaign(self, role="admin"):
        """Test campaign creation"""
        if role not in self.tokens:
            return False, {}
            
        timestamp = int(time.time())
        campaign_data = {
            "name": f"Test Campaign {timestamp}",
            "description": "Test campaign for API testing",
            "objective": "Explorar experiencias organizacionales para testing"
        }
        
        success, response = self.run_test(
            f"Create Campaign ({role})",
            "POST",
            "campaigns/",
            200,
            data=campaign_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            self.campaigns[role] = response
            return True, response
        return False, {}

    def test_list_campaigns(self, role="participant"):
        """Test campaign listing"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"List Campaigns ({role})",
            "GET",
            "campaigns/",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_create_consent(self, role="participant", campaign_id=None):
        """Test consent creation"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            # Use first available campaign
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        consent_data = {
            "campaign_id": campaign_id,
            "accepted": True,
            "consent_text": "Acepto participar en esta campaña de testing"
        }
        
        success, response = self.run_test(
            f"Create Consent ({role})",
            "POST",
            "consents/",
            200,
            data=consent_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            self.consents[role] = response
            return True, response
        return False, {}

    def test_create_session(self, role="participant", campaign_id=None):
        """Test session creation"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        session_data = {
            "campaign_id": campaign_id
        }
        
        success, response = self.run_test(
            f"Create Session ({role})",
            "POST",
            "sessions/",
            200,
            data=session_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            self.sessions[role] = response
            return True, response
        return False, {}

    def test_send_chat_message(self, role="participant", session_id=None):
        """Test sending chat message to VAL"""
        if role not in self.tokens:
            return False, {}
            
        if not session_id:
            if role in self.sessions:
                session_id = self.sessions[role]['id']
            else:
                return False, {}
        
        chat_data = {
            "session_id": session_id,
            "message": "Hola VAL, ¿cómo estás? Esta es una prueba del sistema de chat."
        }
        
        success, response = self.run_test(
            f"Send Chat Message ({role})",
            "POST",
            "chat/message",
            200,
            data=chat_data,
            token=self.tokens[role]
        )
        
        # Wait a bit for AI response
        if success:
            time.sleep(2)
        
        return success, response

    def test_get_chat_history(self, role="participant", session_id=None):
        """Test getting chat history"""
        if role not in self.tokens:
            return False, {}
            
        if not session_id:
            if role in self.sessions:
                session_id = self.sessions[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Chat History ({role})",
            "GET",
            f"chat/history/{session_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_complete_session(self, role="participant", session_id=None):
        """Test session completion"""
        if role not in self.tokens:
            return False, {}
            
        if not session_id:
            if role in self.sessions:
                session_id = self.sessions[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Complete Session ({role})",
            "POST",
            f"sessions/{session_id}/complete",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_dashboard_stats(self, role="admin"):
        """Test dashboard statistics"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"Dashboard Stats ({role})",
            "GET",
            "dashboard/stats",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 2 TESTS - SCRIPTS ==============
    
    def test_create_script(self, role="admin"):
        """Test script creation"""
        if role not in self.tokens:
            return False, {}
            
        timestamp = int(time.time())
        script_data = {
            "name": f"Test Script {timestamp}",
            "description": "Test script for API testing",
            "objective": "Explorar experiencias organizacionales mediante preguntas estructuradas",
            "welcome_message": "¡Hola! Gracias por participar en esta conversación.",
            "closing_message": "Gracias por compartir tu experiencia.",
            "estimated_duration_minutes": 20,
            "steps": [
                {
                    "order": 1,
                    "question": "¿Cómo describirías el ambiente de trabajo en tu equipo?",
                    "description": "Pregunta sobre clima organizacional",
                    "type": "open",
                    "is_required": True,
                    "follow_up_prompt": "Si menciona conflictos, profundizar en las causas"
                },
                {
                    "order": 2,
                    "question": "En una escala del 1 al 10, ¿qué tan satisfecho estás con tu trabajo?",
                    "type": "scale",
                    "is_required": True
                }
            ]
        }
        
        success, response = self.run_test(
            f"Create Script ({role})",
            "POST",
            "scripts/",
            200,
            data=script_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            self.scripts[role] = response
            return True, response
        return False, {}

    def test_list_scripts(self, role="admin"):
        """Test script listing"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"List Scripts ({role})",
            "GET",
            "scripts/",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_get_script(self, role="admin", script_id=None):
        """Test get script by ID"""
        if role not in self.tokens:
            return False, {}
            
        if not script_id:
            if role in self.scripts:
                script_id = self.scripts[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Script ({role})",
            "GET",
            f"scripts/{script_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_update_script(self, role="admin", script_id=None):
        """Test script update (creates new version)"""
        if role not in self.tokens:
            return False, {}
            
        if not script_id:
            if role in self.scripts:
                script_id = self.scripts[role]['id']
            else:
                return False, {}
        
        update_data = {
            "name": f"Updated Test Script {int(time.time())}",
            "objective": "Objetivo actualizado para testing de versiones",
            "steps": [
                {
                    "order": 1,
                    "question": "¿Cómo ha cambiado tu percepción del trabajo remoto?",
                    "type": "open",
                    "is_required": True
                }
            ]
        }
        
        success, response = self.run_test(
            f"Update Script ({role})",
            "PUT",
            f"scripts/{script_id}",
            200,
            data=update_data,
            token=self.tokens[role]
        )
        return success, response

    def test_get_script_versions(self, role="admin", script_id=None):
        """Test get script version history"""
        if role not in self.tokens:
            return False, {}
            
        if not script_id:
            if role in self.scripts:
                script_id = self.scripts[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Script Versions ({role})",
            "GET",
            f"scripts/{script_id}/versions",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_duplicate_script(self, role="admin", script_id=None):
        """Test script duplication"""
        if role not in self.tokens:
            return False, {}
            
        if not script_id:
            if role in self.scripts:
                script_id = self.scripts[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Duplicate Script ({role})",
            "POST",
            f"scripts/{script_id}/duplicate",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 2 TESTS - INVITATIONS ==============
    
    def test_create_invite(self, role="admin", campaign_id=None):
        """Test individual invitation creation"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        timestamp = int(time.time())
        invite_data = {
            "campaign_id": campaign_id,
            "email": f"invite_test_{timestamp}@test.com",
            "message": "Te invitamos a participar en esta campaña de diálogo organizacional"
        }
        
        success, response = self.run_test(
            f"Create Individual Invite ({role})",
            "POST",
            "invites/",
            200,
            data=invite_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            self.invites[f"{role}_individual"] = response
            return True, response
        return False, {}

    def test_create_bulk_invites(self, role="admin", campaign_id=None):
        """Test bulk invitation creation"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        timestamp = int(time.time())
        bulk_invite_data = {
            "campaign_id": campaign_id,
            "emails": [
                f"bulk_test1_{timestamp}@test.com",
                f"bulk_test2_{timestamp}@test.com",
                f"bulk_test3_{timestamp}@test.com"
            ],
            "user_ids": [],
            "message": "Invitación masiva para campaña de testing"
        }
        
        success, response = self.run_test(
            f"Create Bulk Invites ({role})",
            "POST",
            "invites/bulk",
            200,
            data=bulk_invite_data,
            token=self.tokens[role]
        )
        
        if success:
            self.invites[f"{role}_bulk"] = response
            return True, response
        return False, {}

    def test_list_campaign_invites(self, role="admin", campaign_id=None):
        """Test listing invitations for a campaign"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"List Campaign Invites ({role})",
            "GET",
            f"invites/campaign/{campaign_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 2 TESTS - CAMPAIGN UPDATES ==============
    
    def test_update_campaign_with_script(self, role="admin", campaign_id=None, script_id=None):
        """Test updating campaign to assign a script"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
                
        if not script_id:
            if role in self.scripts:
                script_id = self.scripts[role]['id']
            else:
                return False, {}
        
        update_data = {
            "script_id": script_id,
            "description": "Campaña actualizada con guión asignado"
        }
        
        success, response = self.run_test(
            f"Update Campaign with Script ({role})",
            "PUT",
            f"campaigns/{campaign_id}",
            200,
            data=update_data,
            token=self.tokens[role]
        )
        return success, response

    def test_get_campaign_coverage(self, role="admin", campaign_id=None):
        """Test campaign coverage analytics"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Campaign Coverage ({role})",
            "GET",
            f"campaigns/{campaign_id}/coverage",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 3 TESTS - TAXONOMY ==============
    
    def test_create_taxonomy_category(self, role="admin"):
        """Test taxonomy category creation"""
        if role not in self.tokens:
            return False, {}
            
        timestamp = int(time.time())
        category_data = {
            "name": f"Test Category {timestamp}",
            "type": "theme",
            "description": "Test category for API testing",
            "color": "#3B82F6"
        }
        
        success, response = self.run_test(
            f"Create Taxonomy Category ({role})",
            "POST",
            "taxonomy/",
            200,
            data=category_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            if 'taxonomy' not in self.__dict__:
                self.taxonomy = {}
            self.taxonomy[role] = response
            return True, response
        return False, {}

    def test_list_taxonomy_categories(self, role="admin"):
        """Test taxonomy category listing"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"List Taxonomy Categories ({role})",
            "GET",
            "taxonomy/",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_update_taxonomy_category(self, role="admin", category_id=None):
        """Test taxonomy category update"""
        if role not in self.tokens:
            return False, {}
            
        if not category_id:
            if hasattr(self, 'taxonomy') and role in self.taxonomy:
                category_id = self.taxonomy[role]['id']
            else:
                return False, {}
        
        update_data = {
            "name": f"Updated Test Category {int(time.time())}",
            "type": "opportunity",
            "description": "Updated description for testing",
            "color": "#22C55E"
        }
        
        success, response = self.run_test(
            f"Update Taxonomy Category ({role})",
            "PUT",
            f"taxonomy/{category_id}",
            200,
            data=update_data,
            token=self.tokens[role]
        )
        return success, response

    def test_delete_taxonomy_category(self, role="admin", category_id=None):
        """Test taxonomy category deletion"""
        if role not in self.tokens:
            return False, {}
            
        if not category_id:
            if hasattr(self, 'taxonomy') and role in self.taxonomy:
                category_id = self.taxonomy[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Delete Taxonomy Category ({role})",
            "DELETE",
            f"taxonomy/{category_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 3 TESTS - INSIGHTS ==============
    
    def test_create_manual_insight(self, role="admin", campaign_id=None):
        """Test manual insight creation"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        insight_data = {
            "campaign_id": campaign_id,
            "content": "Los empleados valoran mucho la flexibilidad horaria y el trabajo remoto",
            "type": "theme",
            "sentiment": "positive",
            "importance": 8,
            "source_quote": "Me encanta poder trabajar desde casa, es mucho más productivo"
        }
        
        success, response = self.run_test(
            f"Create Manual Insight ({role})",
            "POST",
            "insights/",
            200,
            data=insight_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            if 'insights' not in self.__dict__:
                self.insights = {}
            self.insights[role] = response
            return True, response
        return False, {}

    def test_list_campaign_insights(self, role="admin", campaign_id=None):
        """Test listing insights for a campaign"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"List Campaign Insights ({role})",
            "GET",
            f"insights/campaign/{campaign_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_update_insight(self, role="admin", insight_id=None):
        """Test insight update"""
        if role not in self.tokens:
            return False, {}
            
        if not insight_id:
            if hasattr(self, 'insights') and role in self.insights:
                insight_id = self.insights[role]['id']
            else:
                return False, {}
        
        update_data = {
            "content": "Los empleados valoran la flexibilidad pero necesitan mejor comunicación",
            "sentiment": "mixed",
            "importance": 9
        }
        
        success, response = self.run_test(
            f"Update Insight ({role})",
            "PUT",
            f"insights/{insight_id}",
            200,
            data=update_data,
            token=self.tokens[role]
        )
        return success, response

    def test_validate_insight(self, role="admin", insight_id=None):
        """Test insight validation"""
        if role not in self.tokens:
            return False, {}
            
        if not insight_id:
            if hasattr(self, 'insights') and role in self.insights:
                insight_id = self.insights[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Validate Insight ({role})",
            "PATCH",
            f"insights/{insight_id}/validate?validated=true",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_get_insight_stats(self, role="admin", campaign_id=None):
        """Test insight statistics endpoint"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Insight Stats ({role})",
            "GET",
            f"insights/campaign/{campaign_id}/stats",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_extract_insights(self, role="admin", campaign_id=None):
        """Test AI insight extraction"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Extract Insights ({role})",
            "POST",
            f"insights/campaign/{campaign_id}/extract",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 3 TESTS - TRANSCRIPTS ==============
    
    def test_list_campaign_transcripts(self, role="admin", campaign_id=None):
        """Test listing transcripts for a campaign"""
        if role not in self.tokens:
            return False, {}
            
        if not campaign_id:
            if 'admin' in self.campaigns:
                campaign_id = self.campaigns['admin']['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"List Campaign Transcripts ({role})",
            "GET",
            f"transcripts/campaign/{campaign_id}",
            200,
            token=self.tokens[role]
        )
        
        # Store transcript ID for pseudonymization test
        if success and response and len(response) > 0:
            if 'transcripts' not in self.__dict__:
                self.transcripts = {}
            self.transcripts[role] = response[0]
        
        return success, response

    def test_get_transcript(self, role="admin", transcript_id=None):
        """Test getting a specific transcript"""
        if role not in self.tokens:
            return False, {}
            
        if not transcript_id:
            if hasattr(self, 'transcripts') and role in self.transcripts:
                transcript_id = self.transcripts[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Get Transcript ({role})",
            "GET",
            f"transcripts/{transcript_id}",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_pseudonymize_transcript(self, role="admin", transcript_id=None):
        """Test transcript pseudonymization"""
        if role not in self.tokens:
            return False, {}
            
        if not transcript_id:
            if hasattr(self, 'transcripts') and role in self.transcripts:
                transcript_id = self.transcripts[role]['id']
            else:
                return False, {}
        
        success, response = self.run_test(
            f"Pseudonymize Transcript ({role})",
            "POST",
            f"transcripts/{transcript_id}/pseudonymize",
            200,
            token=self.tokens[role]
        )
        return success, response

    # ============== PHASE 3 TESTS - VALIDATIONS ==============
    
    def test_create_validation_request(self, role="admin", insight_id=None):
        """Test creating validation request (member-checking)"""
        if role not in self.tokens:
            return False, {}
            
        if not insight_id:
            if hasattr(self, 'insights') and role in self.insights:
                insight_id = self.insights[role]['id']
            else:
                return False, {}
        
        validation_data = {
            "insight_id": insight_id,
            "message": "Por favor valida este hallazgo basado en tu experiencia"
        }
        
        success, response = self.run_test(
            f"Create Validation Request ({role})",
            "POST",
            "validations/",
            200,
            data=validation_data,
            token=self.tokens[role]
        )
        
        if success and 'id' in response:
            if 'validations' not in self.__dict__:
                self.validations = {}
            self.validations[role] = response
            return True, response
        return False, {}

    def test_get_pending_validations(self, role="participant"):
        """Test getting pending validations for a user"""
        if role not in self.tokens:
            return False, {}
            
        success, response = self.run_test(
            f"Get Pending Validations ({role})",
            "GET",
            "validations/pending",
            200,
            token=self.tokens[role]
        )
        return success, response

    def test_respond_validation(self, role="participant", validation_id=None):
        """Test responding to a validation request"""
        if role not in self.tokens:
            return False, {}
            
        if not validation_id:
            if hasattr(self, 'validations') and 'admin' in self.validations:
                validation_id = self.validations['admin']['id']
            else:
                return False, {}
        
        response_data = {
            "validated": True,
            "comment": "Sí, este hallazgo refleja mi experiencia en la organización"
        }
        
        success, response = self.run_test(
            f"Respond Validation ({role})",
            "POST",
            f"validations/{validation_id}/respond",
            200,
            data=response_data,
            token=self.tokens[role]
        )
        return success, response

    def run_full_test_suite(self):
        """Run complete test suite"""
        print("🚀 Starting DigiKawsay API Test Suite")
        print("=" * 50)
        
        # 1. Health Check
        self.test_health_check()
        
        # 2. User Registration Tests
        print(f"\n📝 Testing User Registration...")
        self.test_user_registration("participant")
        self.test_user_registration("facilitator") 
        self.test_user_registration("admin")
        
        # 3. User Login Tests (try existing users first)
        print(f"\n🔐 Testing User Login...")
        login_success = False
        
        # Try existing test users first
        if self.test_user_login("admin")[0]:
            login_success = True
        if self.test_user_login("participant")[0]:
            login_success = True
            
        # If login failed, use registered users
        if not login_success:
            print("   Using newly registered users...")
        
        # 4. Get Current User
        print(f"\n👤 Testing User Info...")
        for role in ["admin", "participant"]:
            if role in self.tokens:
                self.test_get_current_user(role)
        
        # 5. Campaign Tests
        print(f"\n📋 Testing Campaigns...")
        
        # Create campaign (admin/facilitator only)
        campaign_created = False
        for role in ["admin", "facilitator"]:
            if role in self.tokens:
                success, campaign_data = self.test_create_campaign(role)
                if success:
                    campaign_created = True
                    # Activate the campaign
                    campaign_id = campaign_data['id']
                    activate_success, _ = self.run_test(
                        f"Activate Campaign ({role})",
                        "PATCH",
                        f"campaigns/{campaign_id}/status?status=active",
                        200,
                        token=self.tokens[role]
                    )
                    break
        
        # List campaigns
        for role in ["admin", "participant"]:
            if role in self.tokens:
                self.test_list_campaigns(role)
        
        # 6. Consent Tests
        print(f"\n✅ Testing Consent...")
        if campaign_created and "participant" in self.tokens:
            campaign_id = None
            for role in ["admin", "facilitator"]:
                if role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    break
            
            if campaign_id:
                self.test_create_consent("participant", campaign_id)
        
        # 7. Session Tests
        print(f"\n💬 Testing Sessions...")
        if "participant" in self.tokens and "participant" in self.consents:
            campaign_id = self.consents["participant"]["campaign_id"]
            session_success, _ = self.test_create_session("participant", campaign_id)
            
            # 8. Chat Tests
            if session_success:
                print(f"\n🤖 Testing VAL Chat...")
                session_id = self.sessions["participant"]["id"]
                
                # Send message
                chat_success, _ = self.test_send_chat_message("participant", session_id)
                
                # Get history
                if chat_success:
                    self.test_get_chat_history("participant", session_id)
                
                # Complete session
                self.test_complete_session("participant", session_id)
        
        # 9. Dashboard Tests
        print(f"\n📊 Testing Dashboard...")
        for role in ["admin", "facilitator"]:
            if role in self.tokens:
                self.test_dashboard_stats(role)
                break
        
        # ============== PHASE 2 TESTS ==============
        
        # 10. Script Tests
        print(f"\n📝 Testing Scripts (Phase 2)...")
        script_created = False
        script_id = None
        
        for role in ["admin", "facilitator"]:
            if role in self.tokens:
                # Create script
                success, script_data = self.test_create_script(role)
                if success:
                    script_created = True
                    script_id = script_data['id']
                    
                    # List scripts
                    self.test_list_scripts(role)
                    
                    # Get script
                    self.test_get_script(role, script_id)
                    
                    # Update script (creates version)
                    self.test_update_script(role, script_id)
                    
                    # Get version history
                    self.test_get_script_versions(role, script_id)
                    
                    # Duplicate script
                    self.test_duplicate_script(role, script_id)
                    
                    break
        
        # 11. Campaign-Script Integration
        print(f"\n🔗 Testing Campaign-Script Integration...")
        if script_created and campaign_created:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    self.test_update_campaign_with_script(role, campaign_id, script_id)
                    break
        
        # 12. Invitation Tests
        print(f"\n📧 Testing Invitations (Phase 2)...")
        if campaign_created:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    
                    # Create individual invite
                    self.test_create_invite(role, campaign_id)
                    
                    # Create bulk invites
                    self.test_create_bulk_invites(role, campaign_id)
                    
                    # List campaign invites
                    self.test_list_campaign_invites(role, campaign_id)
                    
                    break
        
        # 13. Campaign Coverage Analytics
        print(f"\n📈 Testing Campaign Coverage...")
        if campaign_created:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    self.test_get_campaign_coverage(role, campaign_id)
                    break
        
        # ============== PHASE 3 TESTS ==============
        
        # 14. Taxonomy Tests
        print(f"\n🏷️  Testing Taxonomy (Phase 3)...")
        taxonomy_created = False
        category_id = None
        
        for role in ["admin", "facilitator"]:
            if role in self.tokens:
                # Create taxonomy category
                success, category_data = self.test_create_taxonomy_category(role)
                if success:
                    taxonomy_created = True
                    category_id = category_data['id']
                    
                    # List categories
                    self.test_list_taxonomy_categories(role)
                    
                    # Update category
                    self.test_update_taxonomy_category(role, category_id)
                    
                    # Note: We'll delete the category at the end
                    break
        
        # 15. Insights Tests
        print(f"\n💡 Testing Insights (Phase 3)...")
        insight_created = False
        insight_id = None
        
        if campaign_created:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    
                    # Create manual insight
                    success, insight_data = self.test_create_manual_insight(role, campaign_id)
                    if success:
                        insight_created = True
                        insight_id = insight_data['id']
                        
                        # List campaign insights
                        self.test_list_campaign_insights(role, campaign_id)
                        
                        # Update insight
                        self.test_update_insight(role, insight_id)
                        
                        # Validate insight
                        self.test_validate_insight(role, insight_id)
                        
                        # Get insight stats
                        self.test_get_insight_stats(role, campaign_id)
                        
                        # Try to extract insights (may not have transcripts)
                        self.test_extract_insights(role, campaign_id)
                        
                        break
        
        # 16. Transcript Tests
        print(f"\n📝 Testing Transcripts (Phase 3)...")
        transcript_found = False
        
        if campaign_created:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and role in self.campaigns:
                    campaign_id = self.campaigns[role]['id']
                    
                    # List campaign transcripts
                    success, transcripts = self.test_list_campaign_transcripts(role, campaign_id)
                    if success and transcripts and len(transcripts) > 0:
                        transcript_found = True
                        transcript_id = transcripts[0]['id']
                        
                        # Get specific transcript
                        self.test_get_transcript(role, transcript_id)
                        
                        # Pseudonymize transcript
                        self.test_pseudonymize_transcript(role, transcript_id)
                        
                    break
        
        # 17. Validation Tests (Member-checking)
        print(f"\n✅ Testing Validations (Phase 3)...")
        if insight_created and "participant" in self.tokens:
            for role in ["admin", "facilitator"]:
                if role in self.tokens and hasattr(self, 'insights') and role in self.insights:
                    insight_id = self.insights[role]['id']
                    
                    # Create validation request
                    validation_success, _ = self.test_create_validation_request(role, insight_id)
                    
                    # Get pending validations (as participant)
                    self.test_get_pending_validations("participant")
                    
                    # Respond to validation (as participant)
                    if validation_success and hasattr(self, 'validations') and role in self.validations:
                        validation_id = self.validations[role]['id']
                        self.test_respond_validation("participant", validation_id)
                    
                    break
        
        # 18. Cleanup - Delete taxonomy category
        if taxonomy_created and category_id:
            for role in ["admin", "facilitator"]:
                if role in self.tokens:
                    self.test_delete_taxonomy_category(role, category_id)
                    break
        
        # Print Results
        print(f"\n" + "=" * 50)
        print(f"📊 TEST RESULTS")
        print(f"=" * 50)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed < self.tests_run:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['error']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = DigiKawsayAPITester()
    
    try:
        success = tester.run_full_test_suite()
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())