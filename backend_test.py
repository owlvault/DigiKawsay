#!/usr/bin/env python3
"""
DigiKawsay Phase 8 - Hardening Security Backend Testing
Tests all security features including rate limiting, brute force protection, and security management endpoints
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

class SecurityTester:
    def __init__(self, base_url="https://runaflow.preview.emergentagent.com"):
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
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
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
            return True
        return False

    def test_rate_limiting_login(self) -> bool:
        """Test rate limiting on login endpoint - 10 requests/minute"""
        print(f"\n🔍 Testing Login Rate Limiting (10 req/min)...")
        
        # Make 12 rapid login attempts to trigger rate limiting
        attempts = 0
        rate_limited = False
        
        for i in range(12):
            try:
                url = f"{self.base_url}/api/auth/login"
                response = requests.post(
                    url, 
                    json={"email": "test@example.com", "password": "wrongpassword"},
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                attempts += 1
                
                if response.status_code == 429:
                    rate_limited = True
                    print(f"   ✅ Rate limiting triggered after {attempts} attempts")
                    print(f"   ✅ Status: {response.status_code}")
                    break
                elif i < 10:
                    # Small delay between requests
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"   ❌ Error during attempt {i+1}: {str(e)}")
                return False
        
        if rate_limited:
            self.tests_passed += 1
            print(f"   ✅ Rate limiting working correctly")
            return True
        else:
            print(f"   ❌ Rate limiting not triggered after {attempts} attempts")
            self.failed_tests.append({
                'name': 'Login Rate Limiting',
                'error': f'No 429 response after {attempts} attempts'
            })
            return False

    def test_brute_force_protection(self) -> bool:
        """Test brute force protection - 5 failed logins locks account for 15 minutes"""
        print(f"\n🔍 Testing Brute Force Protection...")
        
        test_email = "bruteforce@test.com"
        
        # First, try to register a test user (might fail if exists, that's ok)
        try:
            self.run_test(
                "Register Test User",
                "POST", 
                "auth/register",
                201,
                data={
                    "email": test_email,
                    "password": "correctpassword",
                    "full_name": "Brute Force Test",
                    "role": "participant"
                },
                auth_required=False
            )
        except:
            pass  # User might already exist
        
        # Make 5 failed login attempts
        failed_attempts = 0
        for i in range(5):
            try:
                url = f"{self.base_url}/api/auth/login"
                response = requests.post(
                    url,
                    json={"email": test_email, "password": "wrongpassword"},
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code in [401, 403]:
                    failed_attempts += 1
                    print(f"   Failed attempt {failed_attempts}/5")
                    time.sleep(0.5)  # Small delay between attempts
                    
            except Exception as e:
                print(f"   ❌ Error during failed attempt {i+1}: {str(e)}")
                return False
        
        # Now try the 6th attempt - should be locked
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(
                url,
                json={"email": test_email, "password": "correctpassword"},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 423:  # Locked
                print(f"   ✅ Account locked after 5 failed attempts")
                print(f"   ✅ Status: {response.status_code}")
                self.tests_passed += 1
                return True
            elif response.status_code == 401:
                print(f"   ⚠️  Account not locked, got 401 instead of 423")
                # Check response message for lock indication
                try:
                    resp_data = response.json()
                    if "bloqueada" in resp_data.get("detail", "").lower() or "locked" in resp_data.get("detail", "").lower():
                        print(f"   ✅ Account locked (indicated in message)")
                        self.tests_passed += 1
                        return True
                except:
                    pass
                
                self.failed_tests.append({
                    'name': 'Brute Force Protection',
                    'error': f'Expected 423 or lock message, got {response.status_code}'
                })
                return False
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
                self.failed_tests.append({
                    'name': 'Brute Force Protection',
                    'error': f'Unexpected status {response.status_code}'
                })
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing account lock: {str(e)}")
            self.failed_tests.append({
                'name': 'Brute Force Protection',
                'error': str(e)
            })
            return False

    def test_security_config_endpoint(self) -> bool:
        """Test GET /api/auth/security/config endpoint"""
        success, response = self.run_test(
            "Security Config",
            "GET",
            "auth/security/config",
            200
        )
        
        if success:
            # Validate security config structure
            expected_keys = ['session_timeout_minutes', 'max_login_attempts', 'login_lockout_minutes', 'password_min_length']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in security config: {missing_keys}")
            else:
                print(f"   ✅ Session timeout: {response.get('session_timeout_minutes')} minutes")
                print(f"   ✅ Max login attempts: {response.get('max_login_attempts')}")
                print(f"   ✅ Lockout duration: {response.get('login_lockout_minutes')} minutes")
                print(f"   ✅ Password min length: {response.get('password_min_length')}")
        
        return success

    def test_locked_accounts_endpoint(self) -> bool:
        """Test GET /api/auth/security/locked-accounts endpoint"""
        success, response = self.run_test(
            "Locked Accounts",
            "GET",
            "auth/security/locked-accounts",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} locked accounts")
                if response:
                    # Check first locked account structure
                    first_account = response[0]
                    expected_keys = ['email', 'locked_at', 'failed_attempts']
                    missing_keys = [key for key in expected_keys if key not in first_account]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in locked account: {missing_keys}")
                    else:
                        print(f"   ✅ Sample locked account: {first_account.get('email')}")
                        print(f"   ✅ Failed attempts: {first_account.get('failed_attempts')}")
                else:
                    print(f"   ✅ No locked accounts currently")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_logs_api(self) -> bool:
        """Test logs API"""
        success, response = self.run_test(
            "Logs API",
            "GET",
            "observability/logs?limit=10",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} log entries")
                if response:
                    # Check first log structure
                    first_log = response[0]
                    expected_keys = ['timestamp', 'level', 'message']
                    missing_keys = [key for key in expected_keys if key not in first_log]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in log entry: {missing_keys}")
                    else:
                        print(f"   ✅ Sample log: [{first_log.get('level')}] {first_log.get('message')[:50]}...")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_alerts_api(self) -> bool:
        """Test alerts API"""
        success, response = self.run_test(
            "Alerts API",
            "GET",
            "observability/alerts",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} alerts")
                if response:
                    # Check first alert structure
                    first_alert = response[0]
                    expected_keys = ['id', 'timestamp', 'severity', 'title', 'message']
                    missing_keys = [key for key in expected_keys if key not in first_alert]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in alert: {missing_keys}")
                    else:
                        print(f"   ✅ Sample alert: [{first_alert.get('severity')}] {first_alert.get('title')}")
                else:
                    print(f"   ✅ No active alerts (system healthy)")
            else:
                print(f"   ⚠️  Expected list, got: {type(response)}")
        
        return success

    def test_dashboard_api(self) -> bool:
        """Test dashboard API (comprehensive endpoint)"""
        success, response = self.run_test(
            "Dashboard API",
            "GET",
            "observability/dashboard",
            200
        )
        
        if success:
            # Validate dashboard structure
            expected_sections = ['system', 'business', 'endpoints', 'recent_logs', 'active_alerts', 'health_status']
            missing_sections = [section for section in expected_sections if section not in response]
            if missing_sections:
                print(f"   ⚠️  Missing sections in dashboard: {missing_sections}")
            else:
                print(f"   ✅ Health status: {response.get('health_status')}")
                print(f"   ✅ System metrics: {len(response.get('system', {}))} fields")
                print(f"   ✅ Business metrics: {len(response.get('business', {}))} fields")
                print(f"   ✅ Endpoints: {len(response.get('endpoints', []))}")
                print(f"   ✅ Recent logs: {len(response.get('recent_logs', []))}")
                print(f"   ✅ Active alerts: {len(response.get('active_alerts', []))}")
        
        return success

    def test_prometheus_metrics(self) -> bool:
        """Test Prometheus metrics endpoint"""
        success, response = self.run_test(
            "Prometheus Metrics",
            "GET",
            "observability/metrics/prometheus",
            200,
            headers={'Accept': 'text/plain'}
        )
        
        if success:
            # For Prometheus, response is text, not JSON
            print(f"   ✅ Prometheus metrics available")
        
        return success

def main():
    print("🚀 DigiKawsay Phase 7 - Observability Backend Testing")
    print("=" * 60)
    
    tester = ObservabilityTester()
    
    # Test login first
    if not tester.test_login("admin@test.com", "test123"):
        print("❌ Login failed, stopping tests")
        return 1

    print(f"\n📊 Testing Observability APIs...")
    print("-" * 40)

    # Test all observability endpoints
    test_results = []
    
    # Health check (no auth required)
    test_results.append(tester.test_health_check())
    
    # System metrics
    test_results.append(tester.test_system_metrics())
    
    # Business metrics
    test_results.append(tester.test_business_metrics())
    
    # Endpoint metrics
    test_results.append(tester.test_endpoint_metrics())
    
    # Logs API
    test_results.append(tester.test_logs_api())
    
    # Alerts API
    test_results.append(tester.test_alerts_api())
    
    # Dashboard API (comprehensive)
    test_results.append(tester.test_dashboard_api())
    
    # Prometheus metrics
    test_results.append(tester.test_prometheus_metrics())

    # Print final results
    print(f"\n📈 Test Results Summary")
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
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())