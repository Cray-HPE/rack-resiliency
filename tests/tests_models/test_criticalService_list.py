import unittest
from src.server.models.criticalservice_list import get_critical_services
from mock_data import MOCK_CRITICAL_SERVICES_RESPONSE, MOCK_ERROR_CRT_SVC

class TestCriticalServicesList(unittest.TestCase):
    def test_list_critical_services_success(self):
        result = {"critical-services": get_critical_services(MOCK_CRITICAL_SERVICES_RESPONSE)}
        self.assertIn("critical-services", result)
        self.assertIn("namespace", result["critical-services"])
        self.assertIn("kube-system", result["critical-services"]["namespace"])
        self.assertGreater(len(result["critical-services"]["namespace"]["kube-system"]), 0)
        self.assertTrue(any(service["name"] == "coredns" for service in result["critical-services"]["namespace"]["kube-system"]))
    
    def test_list_critical_services_failure(self):
        result = get_critical_services(MOCK_ERROR_CRT_SVC)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "string indices must be integers")
    
    def test_list_no_services(self):
        result = {"critical-services": get_critical_services({})}
        self.assertIn("critical-services", result)
        self.assertIn("namespace", result["critical-services"])
        self.assertEqual(len(result["critical-services"]["namespace"]), 0)

if __name__ == "__main__":
    unittest.main()