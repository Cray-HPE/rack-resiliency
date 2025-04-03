import json
from kubernetes import client, config
import subprocess
import sys

def get_ceph_details():
    host = 'ncn-m001'
    cmd = f"ssh {host} 'ceph osd tree -f json-pretty'"
    try:
        result = subprocess.run(cmd,shell=True,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,)
        if result.returncode != 0:
            raise ValueError(f"Error fetching Ceph details: {result.stderr}")
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}
 
def get_ceph_hosts():
    host = 'ncn-m001'
    cmd = f"ssh {host} 'ceph orch host ls -f json-pretty'"
    try:
        result = subprocess.run(cmd,shell=True,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,)
        if result.returncode != 0:
            raise ValueError(f"Error fetching Ceph details: {result.stderr}")
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}
 
def get_ceph_storage_nodes():
    """Fetch Ceph storage nodes and their OSD statuses."""
    ceph_tree = get_ceph_details()
    ceph_hosts = get_ceph_hosts()
 
    if isinstance(ceph_tree, dict) and "error" in ceph_tree:
        return {"error": ceph_tree["error"]}
    
    if isinstance(ceph_hosts, dict) and "error" in ceph_hosts:
        return {"error": ceph_hosts["error"]}
 
    host_status_map = {host["hostname"]: host["status"] for host in ceph_hosts}
 
    zones = {}
 
    for item in ceph_tree.get('nodes', []):
        if item['type'] == 'rack':  # Zone (Rack)
            rack_name = item['name']
            storage_nodes = []
 
            for child_id in item.get('children', []):
                host_node = next((x for x in ceph_tree['nodes'] if x['id'] == child_id), None)
 
                if host_node and host_node['type'] == 'host' and host_node['name'].startswith("ncn-s"):
                    osd_ids = host_node.get('children', [])
                    
                    osds = [osd for osd in ceph_tree['nodes'] if osd['id'] in osd_ids and osd['type'] == 'osd']
                    osd_status_list = [{"name": osd['name'], "status": osd.get('status', 'unknown')} for osd in osds]
 
                    node_status = host_status_map.get(host_node['name'], "No Status")
                    if node_status in ["", "online"]:
                        node_status = "Ready"
 
                    storage_nodes.append({
                        "name": host_node['name'],
                        "status": node_status,
                        "osds": osd_status_list
                    })
 
            zones[rack_name] = storage_nodes
 
    return zones if zones else "No Ceph zones present"
 
def load_k8s_config():
    try:
        config.load_kube_config() 
    except Exception as e:
        return {"error": str(e)} 
 
def get_k8s_nodes():
    try:
        load_k8s_config()
        v1 = client.CoreV1Api()
        nodes = v1.list_node().items
        return nodes
    except Exception as e:
        return {"error": str(e)}
 
def get_k8s_nodes_data():
    nodes = get_k8s_nodes()
    if isinstance(nodes, dict) and "error" in nodes:
        return "No k8s topology zone present"
    
    zone_mapping = {}
    for node in nodes:
        node_name = node.metadata.name
        node_status = node.status.conditions[-1].type if node.status.conditions else 'Unknown'
        node_zone = node.metadata.labels.get('topology.kubernetes.io/zone', None)
        if node_zone:
            if node_zone not in zone_mapping:
                zone_mapping[node_zone] = {'masters': [], 'workers': []}
            if node_name.startswith("ncn-m"):
                zone_mapping[node_zone]['masters'].append({"name": node_name, "status": node_status})
            elif node_name.startswith("ncn-w"):
                zone_mapping[node_zone]['workers'].append({"name": node_name, "status": node_status})
    return zone_mapping
 
def main():
    ceph_zones = get_ceph_storage_nodes()
    k8s_zones = get_k8s_nodes_data()
    if isinstance(ceph_zones, dict) and isinstance(k8s_zones, dict):
        print("Ceph and k8s zones are created")
    else:
        print("Zones are not created")
        sys.exit(1)

if __name__ == "__main__":
    print("To check the k8s and ceph zone creation") 
