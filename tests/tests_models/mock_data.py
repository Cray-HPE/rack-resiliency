MOCK_ERROR_CRT_SVC = {"error": "string indices must be integers"} # since func only read json
MOCK_CRITICAL_SERVICES_RESPONSE = {"coredns": {"namespace": "kube-system","type": "Deployment"},"kube-proxy": {"namespace": "kube-system","type": "DaemonSet"}}
MOCK_CRITICAL_SERVICES_UPDATE_FILE = """{"critical-services": {"xyz": {"namespace": "abc","type": "Deployment"},"kube-proxy": {"namespace": "kube-system","type": "DaemonSet"}}}"""
MOCK_ALREADY_EXISTING_FILE = """{"critical-services": {"kube-proxy": {"namespace": "kube-system","type": "DaemonSet"}}}"""
# Mock Kubernetes response
MOCK_K8S_RESPONSE = {
    "x3002":{
       "masters":[
          {
             "name":"ncn-m003",
             "status":"Ready"
          }
       ],
       "workers":[
          {
             "name":"ncn-w003",
             "status":"Ready"
          }
       ]
    }
 }

# Mock Ceph response
MOCK_CEPH_RESPONSE = {
    "x3002":[
       {
          "name":"ncn-s005",
          "status":"Ready",
          "osds": [{"name": "osd.0", "status": "down"}, {"name": "osd.5", "status": "down"}]
       }
    ]
 }

# Mock error response
MOCK_ERROR_RESPONSE = {"error": "Failed to fetch data"}