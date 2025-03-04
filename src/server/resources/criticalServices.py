from kubernetes import client, config
from k8sZones import load_k8s_config
from flask import json

CONFIGMAP_NAME = "rrs-map"
CONFIGMAP_NAMESPACE = "rack-resiliency"  # Change this to the namespace where your ConfigMap is deployed
CONFIGMAP_KEY = "critical-service-config.json"

def get_configmap():
    """Fetch the current ConfigMap data from the Kubernetes cluster."""
    load_k8s_config()
    try:
        v1 = client.CoreV1Api()
        cm = v1.read_namespaced_config_map(CONFIGMAP_NAME, CONFIGMAP_NAMESPACE)
        if CONFIGMAP_KEY in cm.data:
            return json.loads(cm.data[CONFIGMAP_KEY])  # Convert JSON string to Python dictionary
        return {"critical-services": {}}
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ConfigMap: {e}"}