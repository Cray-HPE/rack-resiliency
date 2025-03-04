from kubernetes import client, config
from flask import jsonify
from resources.criticalServices import get_configmap

def isDeploy(resource_type):
     if(resource_type == "Deployment"):
          return "ReplicaSet"
     return resource_type

def get_service_details(service_name):
    """Retrieve details of a specific critical service."""
    try:
        services = get_configmap().get("critical-services", {})
        if service_name not in services:
            return {"error": "Service not found"}
        
        service_info = services[service_name]
        namespace = service_info["namespace"]
        resource_type = service_info["type"]

        # Load Kubernetes config
        config.load_incluster_config()

        v1 = client.CoreV1Api()

        # Get all pods in the namespace and filter by owner reference
        pod_list = v1.list_namespaced_pod(namespace)
        filtered_pods = [
            {
                "name": pod.metadata.name,
                "status": pod.status.phase  # Fetch the status of the pod
            }
            for pod in pod_list.items
            if pod.metadata.owner_references and any(
                owner.kind == isDeploy(resource_type) and owner.name.startswith(service_name)
                for owner in pod.metadata.owner_references
            )
        ]

        # Get all services in the namespace and filter by label selector
        svc_list = v1.list_namespaced_service(namespace)
        filtered_services = [
            svc.metadata.name for svc in svc_list.items
            if svc.spec.selector and any(
                key in svc.spec.selector and svc.spec.selector[key] == service_name
                for key in svc.spec.selector
            )
        ]

        return {
            "Critical Service": {
                "name": service_name,
                "namespace": namespace,
                "type": resource_type,
                "pods": filtered_pods,  # Now includes both name and status
                "services": filtered_services
            }
        }
    except Exception as e:
        return {"error": str(e)}

def describe_service(service_name):
    return jsonify(get_service_details(service_name))