import json
from flask import jsonify, request
from kubernetes import client
from resources.criticalServices import get_configmap, CONFIGMAP_KEY, CONFIGMAP_NAME, CONFIGMAP_NAMESPACE

def update_configmap(new_data):
    """Update the ConfigMap in the Kubernetes cluster with the merged data."""
    try:
        v1 = client.CoreV1Api()
        # Fetch the existing ConfigMap data
        existing_data = get_configmap()
        if "error" in existing_data:
            return existing_data
        
        # Merge the existing and new data
        existing_services = existing_data.get("critical-services", {})
        new_services = json.loads(new_data)

        # Merge new services, checking for duplicates
        added_services = []
        skipped_services = []

        for service_name, details in new_services["critical-services"].items():
            if service_name in existing_services:
                skipped_services.append(service_name)
            else:
                existing_services[service_name] = details
                added_services.append(service_name)

        # Convert back to JSON string for ConfigMap storage
        updated_json_str = json.dumps({"critical-services": existing_services}, indent=2)

        # Patch the ConfigMap with the updated data
        body = {"data": {CONFIGMAP_KEY: updated_json_str}}
        v1.patch_namespaced_config_map(CONFIGMAP_NAME, CONFIGMAP_NAMESPACE, body)

        return {
            "message": "Update successful",
            "added_services": added_services,
            "already_existing_services": skipped_services
        }

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to update ConfigMap: {e}"}

def update_critical_services(new_data):
    """Endpoint to update critical services in the ConfigMap."""
    try:
        # Extract JSON payload from request
        # new_data = request.get_json()
        if not new_data or "new_services" not in new_data:
            return jsonify({"error": "Invalid request format"}), 400

        # Parse the nested JSON string inside "services"
        try:
            new_data = new_data.get("new_services")
            new_services = json.loads(new_data)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format in services"}), 400

        if "critical-services" not in new_services:
            return jsonify({"error": "Missing 'critical-services' in payload"}), 400
        
        result = update_configmap(new_data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
