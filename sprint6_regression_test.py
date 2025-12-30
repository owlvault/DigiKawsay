#!/usr/bin/env python3
"""
DigiKawsay Sprint 6 - Server.py Cleanup Regression Testing
Tests all core endpoints after massive refactoring from 5,331 lines to 310 lines
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

class Sprint6RegressionTester:
    def __init__(self, base_url="https://runa-insights.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.campaign_id = None

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict = None, headers: Dict = None, auth_required: bool = True) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
            
        if auth_required and self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                        if response_data and isinstance(response_data[0], dict):
                            print(f"   First item keys: {list(response_data[0].keys())}")
                    else:
                        print(f"   Response type: {type(response_data)}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'error': str(e)
            })
            return False, {}

    def test_health_check(self) -> bool:
        """Test GET /api/observability/health"""
        success, response = self.run_test(
            "Health Check Endpoint",
            "GET",
            "observability/health",
            200,
            auth_required=False
        )
        
        if success:
            # Validate health response structure
            expected_keys = ['status']
            if 'status' in response:
                print(f"   ✅ Health status: {response.get('status')}")
                if 'database' in response:
                    print(f"   ✅ Database status: {response.get('database')}")
                if 'uptime' in response:
                    print(f"   ✅ Uptime: {response.get('uptime')}")
            else:
                print(f"   ⚠️  No status field in health response")
        
        return success

    def test_admin_login(self) -> bool:
        """Test login with admin@test.com / test123"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@test.com", "password": "test123"},
            auth_required=False
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✅ Token obtained: {self.token[:20]}...")
            
            # Validate login response structure
            expected_keys = ['access_token', 'token_type', 'user']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in login response: {missing_keys}")
            else:
                print(f"   ✅ Token type: {response.get('token_type')}")
                user = response.get('user', {})
                print(f"   ✅ User email: {user.get('email')}")
                print(f"   ✅ User role: {user.get('role')}")
            return True
        return False

    def test_auth_me(self) -> bool:
        """Test GET /api/auth/me"""
        success, response = self.run_test(
            "User Profile Endpoint",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            # Validate user profile structure
            expected_keys = ['email', 'role']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in user profile: {missing_keys}")
            else:
                print(f"   ✅ User email: {response.get('email')}")
                print(f"   ✅ User role: {response.get('role')}")
                if 'full_name' in response:
                    print(f"   ✅ Full name: {response.get('full_name')}")
                if 'tenant_id' in response:
                    print(f"   ✅ Tenant ID: {response.get('tenant_id')}")
        
        return success

    def test_campaigns_list(self) -> bool:
        """Test GET /api/campaigns/ (with trailing slash)"""
        success, response = self.run_test(
            "Campaigns List Endpoint",
            "GET",
            "campaigns/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} campaigns")
                if response:
                    # Store first campaign ID for later tests
                    first_campaign = response[0]
                    if 'id' in first_campaign:
                        self.campaign_id = first_campaign['id']
                        print(f"   ✅ Sample campaign ID: {self.campaign_id}")
                    
                    # Check campaign structure
                    expected_keys = ['id', 'name', 'status']
                    missing_keys = [key for key in expected_keys if key not in first_campaign]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in campaign: {missing_keys}")
                    else:
                        print(f"   ✅ Sample campaign: {first_campaign.get('name')}")
                        print(f"   ✅ Campaign status: {first_campaign.get('status')}")
                else:
                    print(f"   ✅ No campaigns found (empty list)")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_users_list(self) -> bool:
        """Test GET /api/users/"""
        success, response = self.run_test(
            "Users List Endpoint",
            "GET",
            "users/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} users")
                if response:
                    # Check user structure
                    first_user = response[0]
                    expected_keys = ['id', 'email', 'role']
                    missing_keys = [key for key in expected_keys if key not in first_user]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in user: {missing_keys}")
                    else:
                        print(f"   ✅ Sample user: {first_user.get('email')}")
                        print(f"   ✅ User role: {first_user.get('role')}")
                else:
                    print(f"   ✅ No users found (empty list)")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_taxonomy(self) -> bool:
        """Test GET /api/taxonomy/"""
        success, response = self.run_test(
            "Taxonomy Categories Endpoint",
            "GET",
            "taxonomy/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} taxonomy categories")
                if response:
                    # Check taxonomy structure
                    first_category = response[0]
                    expected_keys = ['id', 'name']
                    missing_keys = [key for key in expected_keys if key not in first_category]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in taxonomy: {missing_keys}")
                    else:
                        print(f"   ✅ Sample category: {first_category.get('name')}")
                        if 'description' in first_category:
                            print(f"   ✅ Category description: {first_category.get('description')[:50]}...")
                else:
                    print(f"   ✅ No taxonomy categories found (empty list)")
            elif isinstance(response, dict):
                print(f"   ✅ Taxonomy response keys: {list(response.keys())}")
            else:
                print(f"   ⚠️  Unexpected response type: {type(response)}")
        
        return success

    def test_insights_general(self) -> bool:
        """Test GET /api/insights/"""
        success, response = self.run_test(
            "Insights General Endpoint",
            "GET",
            "insights/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} insights")
                if response:
                    # Check insights structure
                    first_insight = response[0]
                    expected_keys = ['id', 'campaign_id']
                    missing_keys = [key for key in expected_keys if key not in first_insight]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in insight: {missing_keys}")
                    else:
                        print(f"   ✅ Sample insight ID: {first_insight.get('id')}")
                        print(f"   ✅ Campaign ID: {first_insight.get('campaign_id')}")
                else:
                    print(f"   ✅ No insights found (empty list)")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_insights_campaign_specific(self) -> bool:
        """Test GET /api/insights/campaign/{campaign_id}"""
        if not self.campaign_id:
            print(f"   ⚠️  No campaign ID available, skipping campaign-specific insights test")
            return True
        
        success, response = self.run_test(
            "Insights Campaign-Specific Endpoint",
            "GET",
            f"insights/campaign/{self.campaign_id}",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} insights for campaign {self.campaign_id}")
                if response:
                    # Check insights structure
                    first_insight = response[0]
                    expected_keys = ['id', 'campaign_id']
                    missing_keys = [key for key in expected_keys if key not in first_insight]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in campaign insight: {missing_keys}")
                    else:
                        print(f"   ✅ Campaign insight ID: {first_insight.get('id')}")
                        print(f"   ✅ Matches campaign ID: {first_insight.get('campaign_id') == self.campaign_id}")
                else:
                    print(f"   ✅ No insights found for this campaign (empty list)")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_user_registration(self) -> bool:
        """Test POST /api/auth/register (create test user)"""
        test_email = f"test_user_{int(time.time())}@test.com"
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            201,
            data={
                "email": test_email,
                "password": "testpassword123",
                "full_name": "Test User Sprint 6",
                "role": "participant"
            },
            auth_required=False
        )
        
        if success:
            # Validate registration response
            expected_keys = ['id', 'email', 'role']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in registration response: {missing_keys}")
            else:
                print(f"   ✅ New user ID: {response.get('id')}")
                print(f"   ✅ New user email: {response.get('email')}")
                print(f"   ✅ New user role: {response.get('role')}")
                
            # Test login with new user
            print(f"   🔍 Testing login with new user...")
            login_success, login_response = self.run_test(
                "New User Login Test",
                "POST",
                "auth/login",
                200,
                data={"email": test_email, "password": "testpassword123"},
                auth_required=False
            )
            
            if login_success:
                print(f"   ✅ New user can login successfully")
            else:
                print(f"   ❌ New user cannot login")
                return False
        
        return success

def main():
    print("🚀 DigiKawsay Sprint 6 - Server.py Cleanup Regression Testing")
    print("=" * 70)
    print("Testing core endpoints after refactoring from 5,331 to 310 lines")
    print("=" * 70)
    
    tester = Sprint6RegressionTester()
    
    # Test sequence as requested
    test_results = []
    
    # 1. Health check
    test_results.append(tester.test_health_check())
    
    # 2. Login with admin credentials
    if not tester.test_admin_login():
        print("❌ Admin login failed, stopping tests")
        return 1
    test_results.append(True)  # Login was successful
    
    # 3. GET /api/auth/me
    test_results.append(tester.test_auth_me())
    
    # 4. GET /api/campaigns/ (with trailing slash)
    test_results.append(tester.test_campaigns_list())
    
    # 5. GET /api/users/
    test_results.append(tester.test_users_list())
    
    # 6. GET /api/taxonomy/
    test_results.append(tester.test_taxonomy())
    
    # 7. GET /api/insights/ and /api/insights/campaign/{campaign_id}
    test_results.append(tester.test_insights_general())
    test_results.append(tester.test_insights_campaign_specific())
    
    # 8. POST /api/auth/register
    test_results.append(tester.test_user_registration())

    # Print final results
    print(f"\n📈 Sprint 6 Regression Test Results Summary")
    print("=" * 50)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ Failed Tests:")
        for i, failure in enumerate(tester.failed_tests, 1):
            print(f"{i}. {failure['name']}")
            if 'error' in failure:
                print(f"   Error: {failure['error']}")
            else:
                print(f"   Expected: {failure['expected']}, Got: {failure['actual']}")
    else:
        print(f"\n✅ All tests passed! Server.py cleanup was successful.")
        print(f"✅ All core endpoints working after massive refactoring.")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())