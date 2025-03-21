import unittest
from src.server.models.criticalservice_update import update_configmap
from mock_data import MOCK_ERROR_CRT_SVC, MOCK_CRITICAL_SERVICES_UPDATE_FILE, MOCK_CRITICAL_SERVICES_RESPONSE, MOCK_ALREADY_EXISTING_FILE

class TestCriticalServicesUpdate(unittest.TestCase):
    def test_update_critical_service_success(self):
        resp = {"critical-services": MOCK_CRITICAL_SERVICES_RESPONSE}
        result = update_configmap(MOCK_CRITICAL_SERVICES_UPDATE_FILE, resp, True)
        self.assertEqual(result["Update"], "Successful")
        self.assertEqual(result["Successfully Added Services"], ['xyz'])
        self.assertEqual(result["Already Existing Services"], ['kube-proxy'])
    
    def test_update_critical_service_success_already_exist(self):
        resp = {"critical-services": MOCK_CRITICAL_SERVICES_RESPONSE}
        result = update_configmap(MOCK_ALREADY_EXISTING_FILE, resp, True)
        self.assertEqual(result["Update"], "Services Already Exist")
        self.assertEqual(result["Already Existing Services"], ['kube-proxy'])

    def test_update_critical_service_failure(self):
        result = update_configmap(MOCK_ERROR_CRT_SVC, MOCK_CRITICAL_SERVICES_RESPONSE, True)
        self.assertIn("error", result)

if __name__ == "__main__":
    unittest.main()
