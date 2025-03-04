from flask import jsonify
from resources.criticalServices import get_configmap

def get_critical_services():
    """Fetch and format critical services from mounted ConfigMap."""
    try:
        services = get_configmap().get("critical-services", {})
            
        result = [
            {
                "name": name,
                "namespace": details["namespace"],
                "type": details["type"]
            }
            for name, details in services.items()
        ]
            
        return result
    except Exception as e:
        return {"error": str(e)}

def get_critical_service_list():
    """Endpoint to list critical services."""
    return jsonify({"critical-services": get_critical_services()})
