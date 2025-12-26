#!/usr/bin/env python3
"""
DigiKawsay Phase 7 - Observability Backend Testing
Tests all observability endpoints including health, metrics, logs, and alerts
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class ObservabilityTester:
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

    def test_health_check(self) -> bool:
        """Test health check endpoint (no auth required)"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "observability/health",
            200,
            auth_required=False
        )
        
        if success:
            # Validate health response structure
            expected_keys = ['status', 'timestamp', 'uptime_seconds']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in health response: {missing_keys}")
            else:
                print(f"   ✅ Health status: {response.get('status')}")
                print(f"   ✅ Uptime: {response.get('uptime_seconds', 0):.1f} seconds")
        
        return success

    def test_system_metrics(self) -> bool:
        """Test system metrics endpoint"""
        success, response = self.run_test(
            "System Metrics",
            "GET",
            "observability/metrics/system",
            200
        )
        
        if success:
            # Validate system metrics structure
            expected_keys = ['cpu_percent', 'memory_percent', 'memory_used_mb', 'disk_percent', 'active_connections', 'uptime_seconds']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in system metrics: {missing_keys}")
            else:
                print(f"   ✅ CPU: {response.get('cpu_percent', 0):.1f}%")
                print(f"   ✅ Memory: {response.get('memory_percent', 0):.1f}%")
                print(f"   ✅ Disk: {response.get('disk_percent', 0):.1f}%")
                print(f"   ✅ Connections: {response.get('active_connections', 0)}")
        
        return success

    def test_business_metrics(self) -> bool:
        """Test business metrics endpoint"""
        success, response = self.run_test(
            "Business Metrics",
            "GET",
            "observability/metrics/business",
            200
        )
        
        if success:
            # Validate business metrics structure
            expected_keys = ['total_users', 'active_sessions', 'total_campaigns', 'total_insights', 'messages_today', 'insights_generated_today']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in business metrics: {missing_keys}")
            else:
                print(f"   ✅ Users: {response.get('total_users', 0)}")
                print(f"   ✅ Campaigns: {response.get('total_campaigns', 0)}")
                print(f"   ✅ Insights: {response.get('total_insights', 0)}")
                print(f"   ✅ Messages today: {response.get('messages_today', 0)}")
        
        return success

    def test_endpoint_metrics(self) -> bool:
        """Test endpoint metrics"""
        success, response = self.run_test(
            "Endpoint Metrics",
            "GET",
            "observability/metrics/endpoints",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Found {len(response)} endpoint metrics")
                if response:
                    # Check first endpoint structure
                    first_endpoint = response[0]
                    expected_keys = ['endpoint', 'method', 'request_count', 'error_count', 'avg_latency_ms', 'p95_latency_ms', 'p99_latency_ms']
                    missing_keys = [key for key in expected_keys if key not in first_endpoint]
                    if missing_keys:
                        print(f"   ⚠️  Missing keys in endpoint metrics: {missing_keys}")
                    else:
                        print(f"   ✅ Sample endpoint: {first_endpoint.get('method')} {first_endpoint.get('endpoint')}")
                        print(f"   ✅ Requests: {first_endpoint.get('request_count')}, Errors: {first_endpoint.get('error_count')}")
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