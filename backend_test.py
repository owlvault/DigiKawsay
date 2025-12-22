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
                success, _ = self.test_create_campaign(role)
                if success:
                    campaign_created = True
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