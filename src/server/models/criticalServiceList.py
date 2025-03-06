from flask import jsonify
from resources.criticalServices import get_configmap

def get_critical_services():
    """Fetch and format critical services grouped by namespace in the required structure."""
    try:
        services = get_configmap().get("critical-services", {})

        grouped_services = {"namespace": {}}

        for name, details in services.items():
            namespace = details["namespace"]
            if namespace not in grouped_services["namespace"]:
                grouped_services["namespace"][namespace] = []
            grouped_services["namespace"][namespace].append({
                "name": name,
                "type": details["type"]
            })

        return grouped_services
    except Exception as e:
        return {"error": str(e)}

def get_critical_service_list():
    """Endpoint to list critical services."""
    return jsonify({"critical-services": get_critical_services()})

