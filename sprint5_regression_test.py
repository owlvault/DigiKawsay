#!/usr/bin/env python3
"""
DigiKawsay Sprint 5 Regression Test
Tests core endpoints after modular main.py refactoring to ensure stability
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class Sprint5RegressionTester:
    def __init__(self, base_url="https://runa-insights.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.campaign_id = None

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
            self.failed_tests.append({
                'name': name,
                'details': details
            })

    def make_request(self, method: str, endpoint: str, data: Dict = None, auth_required: bool = True) -> tuple:
        """Make HTTP request and return success status and response"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            
            return response.status_code, response.json() if response.content else {}
        except Exception as e:
            return 0, {'error': str(e)}

    def test_health_check(self) -> bool:
        """Test 1: Health check at /api/observability/health"""
        print(f"\n🔍 Testing Health Check Endpoint...")
        
        status_code, response = self.make_request('GET', 'observability/health', auth_required=False)
        
        if status_code == 200:
            if 'status' in response and response['status'] == 'healthy':
                self.log_test("Health Check", True, f"Status: {response['status']}")
                return True
            else:
                self.log_test("Health Check", False, f"Invalid response structure: {response}")
                return False
        else:
            self.log_test("Health Check", False, f"Status: {status_code}, Response: {response}")
            return False

    def test_admin_login(self) -> bool:
        """Test 2: Login with admin@test.com / test123"""
        print(f"\n🔍 Testing Admin Login...")
        
        login_data = {
            "email": "admin@test.com",
            "password": "test123"
        }
        
        status_code, response = self.make_request('POST', 'auth/login', login_data, auth_required=False)
        
        if status_code == 200:
            if 'access_token' in response and 'user' in response:
                self.token = response['access_token']
                user = response['user']
                self.log_test("Admin Login", True, f"User: {user.get('email')}, Role: {user.get('role')}")
                return True
            else:
                self.log_test("Admin Login", False, f"Missing token or user in response: {response}")
                return False
        else:
            self.log_test("Admin Login", False, f"Status: {status_code}, Response: {response}")
            return False

    def test_auth_me(self) -> bool:
        """Test 3: Verify GET /api/auth/me"""
        print(f"\n🔍 Testing Auth Me Endpoint...")
        
        status_code, response = self.make_request('GET', 'auth/me')
        
        if status_code == 200:
            required_fields = ['id', 'email', 'role', 'full_name']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                self.log_test("Auth Me", True, f"Email: {response.get('email')}, Role: {response.get('role')}")
                return True
            else:
                self.log_test("Auth Me", False, f"Missing fields: {missing_fields}")
                return False
        else:
            self.log_test("Auth Me", False, f"Status: {status_code}, Response: {response}")
            return False

    def test_campaigns_list(self) -> bool:
        """Test 4: Verify GET /api/campaigns"""
        print(f"\n🔍 Testing Campaigns List Endpoint...")
        
        # Try both with and without trailing slash
        for endpoint in ['campaigns', 'campaigns/']:
            status_code, response = self.make_request('GET', endpoint)
            
            if status_code == 200:
                if isinstance(response, list):
                    if response:  # If we have campaigns, store the first one's ID
                        self.campaign_id = response[0].get('id')
                    self.log_test("Campaigns List", True, f"Found {len(response)} campaigns (endpoint: {endpoint})")
                    return True
                else:
                    self.log_test("Campaigns List", False, f"Expected list, got: {type(response)}")
                    return False
        
        self.log_test("Campaigns List", False, f"Both endpoints failed. Last status: {status_code}")
        return False

    def test_insights_list(self) -> bool:
        """Test 5: Verify GET /api/insights (list)"""
        print(f"\n🔍 Testing Insights List Endpoint...")
        
        status_code, response = self.make_request('GET', 'insights')
        
        if status_code == 200:
            if isinstance(response, list):
                self.log_test("Insights List", True, f"Found {len(response)} insights")
                return True
            else:
                self.log_test("Insights List", False, f"Expected list, got: {type(response)}")
                return False
        else:
            self.log_test("Insights List", False, f"Status: {status_code}, Response: {response}")
            return False

    def test_network_snapshots(self) -> bool:
        """Test 6: Verify GET /api/network/snapshots/{campaign_id}"""
        print(f"\n🔍 Testing Network Snapshots Endpoint...")
        
        if not self.campaign_id:
            # Try to get a campaign ID first
            status_code, campaigns = self.make_request('GET', 'campaigns/')
            if status_code == 200 and isinstance(campaigns, list) and campaigns:
                self.campaign_id = campaigns[0].get('id')
            
            if not self.campaign_id:
                self.log_test("Network Snapshots", False, "No campaign_id available for testing")
                return False
        
        endpoint = f'network/snapshots/{self.campaign_id}'
        status_code, response = self.make_request('GET', endpoint)
        
        if status_code == 200:
            if isinstance(response, list):
                self.log_test("Network Snapshots", True, f"Found {len(response)} snapshots for campaign {self.campaign_id}")
                return True
            else:
                self.log_test("Network Snapshots", False, f"Expected list, got: {type(response)}")
                return False
        elif status_code == 404:
            # No snapshots for this campaign is acceptable
            self.log_test("Network Snapshots", True, f"No snapshots found for campaign {self.campaign_id} (404 is acceptable)")
            return True
        else:
            self.log_test("Network Snapshots", False, f"Status: {status_code}, Response: {response}")
            return False

    def run_regression_tests(self) -> bool:
        """Run all Sprint 5 regression tests"""
        print("🚀 DigiKawsay Sprint 5 Regression Test")
        print("Testing core endpoints after modular main.py refactoring")
        print("=" * 60)
        
        # Test sequence as requested
        tests = [
            self.test_health_check,
            self.test_admin_login,
            self.test_auth_me,
            self.test_campaigns_list,
            self.test_insights_list,
            self.test_network_snapshots
        ]
        
        all_passed = True
        for test in tests:
            try:
                result = test()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {str(e)}")
                self.failed_tests.append({
                    'name': test.__name__,
                    'details': f"Exception: {str(e)}"
                })
                all_passed = False
        
        return all_passed

    def print_summary(self):
        """Print test summary"""
        print(f"\n📈 Sprint 5 Regression Test Summary")
        print("=" * 40)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for i, failure in enumerate(self.failed_tests, 1):
                print(f"{i}. {failure['name']}: {failure['details']}")
        else:
            print(f"\n✅ All tests passed! Sprint 5 refactoring is stable.")

def main():
    tester = Sprint5RegressionTester()
    
    success = tester.run_regression_tests()
    tester.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())