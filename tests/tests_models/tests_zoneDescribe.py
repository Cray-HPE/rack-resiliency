import unittest
from src.server.models.zoneDescribe import get_zone_info
from mock_data import MOCK_K8S_RESPONSE, MOCK_ERROR_RESPONSE, MOCK_CEPH_RESPONSE

class TestZoneDescribe(unittest.TestCase):
    def test_describe_zone_success(self):
        result = get_zone_info("x3002", MOCK_K8S_RESPONSE, MOCK_CEPH_RESPONSE)
        self.assertIn("Zone Name", result)
        self.assertEqual(result["Zone Name"], "x3002")

    def test_describe_zone_no_k8s_data(self):
        result = get_zone_info("x3002", MOCK_ERROR_RESPONSE, MOCK_CEPH_RESPONSE)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to fetch data")

    def test_describe_zone_no_ceph_data(self):
        result = get_zone_info("x3002", MOCK_K8S_RESPONSE, MOCK_ERROR_RESPONSE)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to fetch data")

    def test_describe_zone_not_found(self):
        result = get_zone_info("zoneX", MOCK_K8S_RESPONSE, MOCK_CEPH_RESPONSE)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Zone not found")


if __name__ == "__main__":
    unittest.main()