#!/usr/bin/env python3
"""
DigiKawsay Sprint 4 - Router Migration Regression Test
Quick regression test to verify backend endpoints after router refactoring
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

class RegressionTester:
    def __init__(self, base_url="https://runa-insights.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

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
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "observability/health",
            200,
            auth_required=False
        )
        
        if success:
            status = response.get('status', 'unknown')
            print(f"   ✅ Health status: {status}")
            if 'uptime' in response:
                print(f"   ✅ Uptime: {response.get('uptime')}")
            if 'version' in response:
                print(f"   ✅ Version: {response.get('version')}")
        
        return success

    def test_login(self, email: str, password: str) -> bool:
        """Test login and get token"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password},
            auth_required=False
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✅ Token obtained: {self.token[:20]}...")
            user = response.get('user', {})
            print(f"   ✅ User: {user.get('email')} ({user.get('role')})")
            return True
        return False

    def test_auth_me(self) -> bool:
        """Test GET /api/auth/me endpoint"""
        success, response = self.run_test(
            "Auth Me",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            print(f"   ✅ User ID: {response.get('id')}")
            print(f"   ✅ Email: {response.get('email')}")
            print(f"   ✅ Role: {response.get('role')}")
            print(f"   ✅ Active: {response.get('is_active')}")
        
        return success

    def test_campaigns(self) -> bool:
        """Test GET /api/campaigns endpoint"""
        success, response = self.run_test(
            "Campaigns List",
            "GET",
            "campaigns/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} campaigns")
                if response:
                    first_campaign = response[0]
                    print(f"   ✅ Sample campaign: {first_campaign.get('name')}")
                    print(f"   ✅ Status: {first_campaign.get('status')}")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_users(self) -> bool:
        """Test GET /api/users endpoint (admin required)"""
        success, response = self.run_test(
            "Users List",
            "GET",
            "users/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} users")
                if response:
                    first_user = response[0]
                    print(f"   ✅ Sample user: {first_user.get('email')}")
                    print(f"   ✅ Role: {first_user.get('role')}")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_taxonomy(self) -> bool:
        """Test GET /api/taxonomy endpoint"""
        success, response = self.run_test(
            "Taxonomy Categories",
            "GET",
            "taxonomy/",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} taxonomy categories")
                if response:
                    first_category = response[0]
                    print(f"   ✅ Sample category: {first_category.get('name')}")
                    print(f"   ✅ Type: {first_category.get('type')}")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

def main():
    print("🚀 DigiKawsay Sprint 4 - Router Migration Regression Test")
    print("=" * 60)
    print("Testing core endpoints after router refactoring...")
    
    tester = RegressionTester()
    
    # Test sequence as requested
    test_results = []
    
    # 1. Health check
    test_results.append(tester.test_health_check())
    
    # 2. Login with admin credentials
    if not tester.test_login("admin@test.com", "test123"):
        print("❌ Admin login failed, stopping tests")
        return 1
    
    # 3. Test auth/me
    test_results.append(tester.test_auth_me())
    
    # 4. Test campaigns
    test_results.append(tester.test_campaigns())
    
    # 5. Test users (admin required)
    test_results.append(tester.test_users())
    
    # 6. Test taxonomy
    test_results.append(tester.test_taxonomy())

    # Print final results
    print(f"\n📈 Regression Test Results Summary")
    print("=" * 40)
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
        print(f"\n✅ All regression tests passed! Router migration successful.")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())