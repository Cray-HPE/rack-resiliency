from flask import jsonify
from resources.criticalServices import *
from kubernetes import client

def get_service_details(service_name):
    """Retrieve details of a specific critical service."""
    try:
        services = get_configmap().get("critical-services", {})
        if service_name not in services:
            return {"error": "Service not found"}
        
        service_info = services[service_name]
        namespace = service_info["namespace"]
        resource_type = service_info["type"]

        # Get all pods in the namespace and filter by owner reference
        filtered_pods, total_pods, running_pods = get_namespaced_pods(service_info, service_name)

        # Get all services in the namespace and filter by label selector
        filtered_services = get_namespaced_services(service_info, service_name)
        
        # Get configured instances
        apps_v1 = client.AppsV1Api()
        configured_instances = None
        if resource_type == "Deployment":
            deployment = apps_v1.read_namespaced_deployment(service_name, namespace)
            configured_instances = deployment.spec.replicas
        elif resource_type == "StatefulSet":
            statefulset = apps_v1.read_namespaced_stateful_set(service_name, namespace)
            configured_instances = statefulset.spec.replicas
        elif resource_type == "DaemonSet":
            daemonset = apps_v1.read_namespaced_daemon_set(service_name, namespace)
            configured_instances = daemonset.status.desired_number_scheduled

        return {
            "Critical Service": {
                "name": service_name,
                "namespace": namespace,
                "type": resource_type,
                "configured_instances": configured_instances,
                "currently_running_instances": running_pods,  # Running pod count
                "total_pods": total_pods,
                "pods": filtered_pods,  # Now includes both name and status
                "services": filtered_services
            }
        }
    except Exception as e:
        return {"error": str(e)}

def describe_service(service_name):
    return jsonify(get_service_details(service_name))