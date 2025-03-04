from kubernetes import client, config

def load_k8s_config():
    """Load Kubernetes configuration for API access."""
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

def get_k8s_nodes():
    """Retrieve all Kubernetes nodes."""
    try:
        load_k8s_config()
        v1 = client.CoreV1Api()
        return v1.list_node().items
    except Exception as e:
        return {"error": str(e)}

def get_pods(namespace):
    """Retrieve all Kubernetes nodes."""
    try:
        load_k8s_config()
        v1 = client.CoreV1Api()
        return v1.list_namespaced_pod(namespace)
    except Exception as e:
        return {"error": str(e)}

def get_services(namespace):
    """Retrieve all Kubernetes nodes."""
    try:
        load_k8s_config()
        v1 = client.CoreV1Api()
        return v1.list_namespaced_service(namespace)
    except Exception as e:
        return {"error": str(e)}

def get_k8s_nodes_data():
    """Fetch Kubernetes nodes and organize them by topology zone."""
    nodes = get_k8s_nodes()

    if isinstance(nodes, dict) and "error" in nodes:
        return {"error": nodes["error"]}

    zone_mapping = {}

    for node in nodes:
        node_name = node.metadata.name
        node_status = node.status.conditions[-1].type if node.status.conditions else 'Unknown'
        node_zone = node.metadata.labels.get('topology.kubernetes.io/zone', None)

        if node_zone:
            if node_zone not in zone_mapping:
                zone_mapping[node_zone] = {'masters': [], 'workers': []}

            if node_name.startswith("ncn-m"):
                zone_mapping[node_zone]['masters'].append({"name": node_name, "status": node_status})
            elif node_name.startswith("ncn-w"):
                zone_mapping[node_zone]['workers'].append({"name": node_name, "status": node_status})

    return zone_mapping if zone_mapping else "No K8s topology zone present"
