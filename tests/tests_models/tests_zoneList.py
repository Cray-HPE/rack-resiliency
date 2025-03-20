import unittest
from src.server.models.zoneList import map_zones
from mock_data import MOCK_K8S_RESPONSE, MOCK_ERROR_RESPONSE, MOCK_CEPH_RESPONSE

class TestZoneMapping(unittest.TestCase):
    def test_zone_mapping_success(self):
        result = map_zones(MOCK_K8S_RESPONSE, MOCK_CEPH_RESPONSE)
        self.assertIn("Zones", result)
        self.assertGreater(len(result["Zones"]), 0)
        self.assertTrue(any(zone["Zone Name"] == "zone1" for zone in result["Zones"]))
    
    def test_k8s_api_failure(self):
        result = map_zones(MOCK_ERROR_RESPONSE, MOCK_CEPH_RESPONSE)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to fetch data")
    
    def test_ceph_api_failure(self):
        result = map_zones(MOCK_K8S_RESPONSE, MOCK_ERROR_RESPONSE)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to fetch data")
    
    def test_no_zones_configured(self):
        result = map_zones("No K8s topology zone present", "No Ceph zones present")
        self.assertIn("Zones", result)
        self.assertEqual(len(result["Zones"]), 0)
        self.assertEqual(result.get("Information"), "No zones (K8s topology and Ceph) configured")
    
    def test_node_status(self):
        result = map_zones(MOCK_K8S_RESPONSE, MOCK_CEPH_RESPONSE)
        zone = next(zone for zone in result["Zones"] if zone["Zone Name"] == "zone1")
        self.assertIn("Kubernetes Topology Zone", zone)
        self.assertIn("Management Master Nodes", zone["Kubernetes Topology Zone"])
        self.assertIn("ncn-m001", zone["Kubernetes Topology Zone"]["Management Master Nodes"])
        self.assertIn("CEPH Zone", zone)
        self.assertIn("Management Storage Nodes", zone["CEPH Zone"])
        self.assertIn("ncn-s001", zone["CEPH Zone"]["Management Storage Nodes"])

if __name__ == "__main__":
    unittest.main()
