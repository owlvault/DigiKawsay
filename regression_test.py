#!/usr/bin/env python3
"""
DigiKawsay Sprint 3 - Regression Test
Quick regression test to verify backend functionality after service migration
"""

import requests
import sys
import json
import time
from datetime import datetime

class RegressionTester:
    def __init__(self, base_url="https://runa-insights.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
            self.failed_tests.append({"name": name, "details": details})

    def test_health_check(self) -> bool:
        """Test 1: Health check at /api/observability/health"""
        print(f"\n🔍 Testing Health Check...")
        try:
            url = f"{self.base_url}/api/observability/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    self.log_test("Health Check", True, f"- Status: {status}")
                    return True
                except:
                    self.log_test("Health Check", True, f"- Status: {response.status_code}")
                    return True
            else:
                self.log_test("Health Check", False, f"- Status: {response.status_code}, Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"- Error: {str(e)}")
            return False

    def test_login(self) -> bool:
        """Test 2: Login with admin@test.com / test123"""
        print(f"\n🔍 Testing Admin Login...")
        try:
            url = f"{self.base_url}/api/auth/login"
            data = {"email": "admin@test.com", "password": "test123"}
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    resp_data = response.json()
                    if 'access_token' in resp_data:
                        self.token = resp_data['access_token']
                        user = resp_data.get('user', {})
                        self.log_test("Admin Login", True, f"- Token obtained, User: {user.get('email', 'unknown')}")
                        return True
                    else:
                        self.log_test("Admin Login", False, "- No access_token in response")
                        return False
                except:
                    self.log_test("Admin Login", False, "- Invalid JSON response")
                    return False
            else:
                self.log_test("Admin Login", False, f"- Status: {response.status_code}, Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("Admin Login", False, f"- Error: {str(e)}")
            return False

    def test_auth_me(self) -> bool:
        """Test 3: Verify /api/auth/me returns user data"""
        print(f"\n🔍 Testing Auth Me Endpoint...")
        if not self.token:
            self.log_test("Auth Me", False, "- No token available")
            return False
            
        try:
            url = f"{self.base_url}/api/auth/me"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    email = data.get('email', 'unknown')
                    role = data.get('role', 'unknown')
                    self.log_test("Auth Me", True, f"- Email: {email}, Role: {role}")
                    return True
                except:
                    self.log_test("Auth Me", False, "- Invalid JSON response")
                    return False
            else:
                self.log_test("Auth Me", False, f"- Status: {response.status_code}, Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("Auth Me", False, f"- Error: {str(e)}")
            return False

    def test_campaigns(self) -> bool:
        """Test 4: Verify /api/campaigns returns a list"""
        print(f"\n🔍 Testing Campaigns Endpoint...")
        if not self.token:
            self.log_test("Campaigns", False, "- No token available")
            return False
            
        try:
            url = f"{self.base_url}/api/campaigns/"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        self.log_test("Campaigns", True, f"- Found {len(data)} campaigns")
                        return True
                    else:
                        self.log_test("Campaigns", False, f"- Expected list, got {type(data)}")
                        return False
                except:
                    self.log_test("Campaigns", False, "- Invalid JSON response")
                    return False
            else:
                self.log_test("Campaigns", False, f"- Status: {response.status_code}, Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("Campaigns", False, f"- Error: {str(e)}")
            return False

    def test_logout_simulation(self) -> bool:
        """Test 5: Logout simulation (no specific endpoint needed)"""
        print(f"\n🔍 Testing Logout Simulation...")
        if self.token:
            # Simply clear the token to simulate logout
            self.token = None
            self.log_test("Logout Simulation", True, "- Token cleared successfully")
            return True
        else:
            self.log_test("Logout Simulation", False, "- No token to clear")
            return False

def main():
    print("🚀 DigiKawsay Sprint 3 - Regression Test")
    print("Verificando funcionalidad básica después de migración de servicios")
    print("=" * 70)
    
    tester = RegressionTester()
    
    # Run all regression tests
    test_results = []
    
    # Test 1: Health check
    test_results.append(tester.test_health_check())
    
    # Test 2: Login
    test_results.append(tester.test_login())
    
    # Test 3: Auth me (requires login)
    test_results.append(tester.test_auth_me())
    
    # Test 4: Campaigns (requires login)
    test_results.append(tester.test_campaigns())
    
    # Test 5: Logout simulation
    test_results.append(tester.test_logout_simulation())
    
    # Print final results
    print(f"\n📈 Regression Test Results")
    print("=" * 40)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ Failed Tests:")
        for i, failure in enumerate(tester.failed_tests, 1):
            print(f"{i}. {failure['name']}: {failure['details']}")
    else:
        print(f"\n✅ All regression tests passed!")
        print(f"✅ Backend functionality verified after service migration")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())