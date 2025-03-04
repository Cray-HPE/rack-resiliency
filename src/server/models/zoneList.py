from resources.k8sZones import get_k8s_nodes_data
from resources.cephZones import get_ceph_storage_nodes
from flask import jsonify

def zoneExist(k8s_zone_mapping, ceph_zones):
    if (type(k8s_zone_mapping) == str) and (type(ceph_zones) == str):
        return {"Information": "No zones(k8s topology and ceph) configured"}
    if type(k8s_zone_mapping) == str:
        return {"Information": "No K8s topology zones configured"}
    if type(ceph_zones) == str:
        return {"Information": "No CEPH zones configured"}

def get_node_name(node_list):
    names = []
    if(len(node_list)>0):
        for i in node_list:
            names.append(i.get("name"))
    return names

def map_zones():
    """Map Kubernetes and Ceph zones and provide summarized data."""
    k8s_zone_mapping = get_k8s_nodes_data()
    ceph_zones = get_ceph_storage_nodes()

    if isinstance(k8s_zone_mapping, dict) and "error" in k8s_zone_mapping:
        return {"error": k8s_zone_mapping["error"]}
    
    if isinstance(ceph_zones, dict) and "error" in ceph_zones:
        return {"error": ceph_zones["error"]}
    
    if (type(k8s_zone_mapping) == str) or (type(ceph_zones) == str):
        return zoneExist(k8s_zone_mapping, ceph_zones)
    
    all_zone_names = set(k8s_zone_mapping.keys()) | set(ceph_zones.keys())
    result = {}

    for zone_name in all_zone_names:
        masters = get_node_name(k8s_zone_mapping.get(zone_name, {}).get("masters", []))
        workers = get_node_name(k8s_zone_mapping.get(zone_name, {}).get("workers", []))
        storage = get_node_name(ceph_zones.get(zone_name, []))

        result[zone_name] = {
            "Management Master Nodes": masters,
            "Management Worker Nodes": workers,
            "Management Storage Nodes": storage
        }

    return result

def get_zones():
    """Endpoint to get summary of all zones."""
    return jsonify(map_zones())