import os
import json
from flask import jsonify

CRITICAL_SERVICE_CONFIG_PATH = "/etc/config"

def get_critical_services():
    """Fetch and format critical services from mounted ConfigMap."""
    try:
        if not os.path.exists(CRITICAL_SERVICE_CONFIG_PATH):
            return {"error": "Critical service config file not found"}
        
        with open(CRITICAL_SERVICE_CONFIG_PATH, 'r') as file:
            config_data = json.load(file)
            services = config_data.get("critical-services", {})

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
