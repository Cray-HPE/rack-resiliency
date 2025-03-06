#
# MIT License
#
# (C) Copyright [2024-2025] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

from kubernetes import client, config
from flask import json

CONFIGMAP_NAME = "rrs-map"
CONFIGMAP_NAMESPACE = "rack-resiliency"  # Change this to the namespace where your ConfigMap is deployed
CONFIGMAP_KEY = "critical-service-config.json"

config.load_incluster_config()

def get_namespaced_pods(service_info, service_name):
    namespace = service_info["namespace"]
    resource_type = service_info["type"]
    v1 = client.CoreV1Api()

    # Get all pods in the namespace and filter by owner reference
    pod_list = v1.list_namespaced_pod(namespace)
    running_pods = 0
    total_pods = 0

    result = []
    for pod in pod_list.items:
        if pod.metadata.owner_references and any(
            owner.kind == isDeploy(resource_type) and owner.name.startswith(service_name)
            for owner in pod.metadata.owner_references
        ):
            total_pods += 1
            if pod.status.phase == "Running":
                running_pods += 1
            result.append({
                "name": pod.metadata.name,
                "status": pod.status.phase
            })
    return result, running_pods, total_pods

def get_namespaced_services(service_info, service_name):
    namespace = service_info["namespace"]
    resource_type = service_info["type"]
    v1 = client.CoreV1Api()

    # Get all services in the namespace and filter by owner reference
    svc_list = v1.list_namespaced_service(namespace)
    result = [
        svc.metadata.name for svc in svc_list.items
        if svc.spec.selector and any(
            key in svc.spec.selector and svc.spec.selector[key] == service_name
            for key in svc.spec.selector
        )
    ]
    return result

def isDeploy(resource_type):
     if(resource_type == "Deployment"):
          return "ReplicaSet"
     return resource_type


def get_configmap():
    """Fetch the current ConfigMap data from the Kubernetes cluster."""
    try:
        v1 = client.CoreV1Api()
        cm = v1.read_namespaced_config_map(CONFIGMAP_NAME, CONFIGMAP_NAMESPACE)
        if CONFIGMAP_KEY in cm.data:
            return json.loads(cm.data[CONFIGMAP_KEY])  # Convert JSON string to Python dictionary
        return {"critical-services": {}}
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ConfigMap: {e}"}