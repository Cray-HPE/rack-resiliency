import unittest
from src.server.models.criticalServiceDescribe import get_service_details
from mock_data import MOCK_ERROR_CRT_SVC, MOCK_CRITICAL_SERVICES_RESPONSE

class TestCriticalServicesDescribe(unittest.TestCase):
    def test_describe_critical_service_success(self):
        result = get_service_details(MOCK_CRITICAL_SERVICES_RESPONSE, "coredns")
        self.assertIn("Critical Service", result)
        self.assertIn("Name", result["Critical Service"])
        self.assertEqual(result["Critical Service"]["Name"], "coredns")
        self.assertIn("Type", result["Critical Service"])
        self.assertEqual(result["Critical Service"]["Type"], "Deployment")
    def test_describe_critical_service_not_found(self):
        result = get_service_details(MOCK_CRITICAL_SERVICES_RESPONSE,"unknown-service")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Service not found")
    
    def test_describe_critical_service_failure(self):
        result = get_service_details(MOCK_ERROR_CRT_SVC, "coredns")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Service not found")

if __name__ == "__main__":
    unittest.main()