from flask import jsonify
from resources.k8sDetails import get_k8s_nodes_data
from resources.cephDetails import get_ceph_storage_nodes
from models.zoneUtils import zoneExist

# zone_desc_bp = Blueprint('zone_desc', __name__)

# @zone_desc_bp.route('/zones/<zone_name>', methods=['GET'])
def describe_zone(zone_name):
    """Endpoint to get detailed information of a specific zone."""
    k8s_zone_mapping = get_k8s_nodes_data()
    ceph_zones = get_ceph_storage_nodes()

    if isinstance(k8s_zone_mapping, dict) and "error" in k8s_zone_mapping:
        return jsonify({"error": k8s_zone_mapping["error"]})
    
    if isinstance(ceph_zones, dict) and "error" in ceph_zones:
        return jsonify({"error": ceph_zones["error"]})
    
    if (type(k8s_zone_mapping) == str) or (type(ceph_zones) == str):
        return zoneExist(k8s_zone_mapping, ceph_zones)

    masters = k8s_zone_mapping.get(zone_name, {}).get("masters", [])
    workers = k8s_zone_mapping.get(zone_name, {}).get("workers", [])
    storage = ceph_zones.get(zone_name, [])

    if not (masters or workers or storage):
        return jsonify({"error": "Zone not found"})

    return jsonify({
        "zone_name": zone_name,
        "no_of_masters": len(masters),
        "no_of_workers": len(workers),
        "no_of_storage": len(storage),
        "nodes": {
            "masters": masters,
            "workers": workers,
            "storage": storage
        }
    })
