from kubernetes import client, config
from pprint import pprint
import ast
from prettytable import PrettyTable, ALL
import socket
import sys

c_services_data = PrettyTable(["Service", "namespace", "Type", "Pods", "Total Replicas", "Available Replicas", "Pod(s)/zone", "Observations"], hrules=ALL)
c_services_data.align = "l"
zone_node_map = dict()

def find_hostname(ip:str) ->str:
    """Get hostname from ip address

    Args:
        ip (str): ip address of the node where Pod is executing
    """
    try:
        hostname = socket.gethostbyaddr(ip)[1]
        return hostname
    except socket.herror:
        return None
    
def zone_lookup(hostname:str) -> str:
    """Look for hostname in zone map

    Args:
        hostname (str): Name of the host
    """
    for k,v in zone_node_map.items():
        if hostname in v:
            return k
    return None


def check_distribution_and_report(o_name: str, o_nspace: str, o_replicas :int, o_type: str):
    """_summary_

    Args:
        o_name (_type_): Name of the object
        o_nspace (_type_): Namespace
        o_replicas (_type_): Replicas configured to run
        o_type (_type_): Type of the Object
    """
    global c_services_data
    apps_api = client.AppsV1Api()
    core_api= client.CoreV1Api()
    if o_type == "Deployment":
       try:
          deploy = apps_api.read_namespaced_deployment(name=o_name, namespace=o_nspace)          
          revision = deploy.metadata.annotations["deployment.kubernetes.io/revision"]
          
          rs_for_deploy = apps_api.list_namespaced_replica_set(namespace=o_nspace)
          for rs in rs_for_deploy.items:
              if rs.metadata.annotations["deployment.kubernetes.io/revision"] == revision:
                  hash_label = rs.metadata.labels["pod-template-hash"]
                  break
              
          pod_for_deploy = core_api.list_namespaced_pod(namespace=o_nspace, label_selector=f"pod-template-hash={hash_label}")
          if pod_for_deploy is not None:
              pod_list = list()
              zone_pod_map = dict()
              for pod in pod_for_deploy.items:
                  pod_list.append(pod.metadata.name)
                  node_name = find_hostname(pod.status.host_ip)
                  if node_name[0] is not None:
                      zone = zone_lookup(node_name[0])
                      if zone not in zone_pod_map.keys():
                        nlist = list()
                        nlist.append(node_name[0])
                        zone_pod_map[zone] = nlist                        
                      else:
                        nlist = zone_pod_map[zone]
                        nlist.append(node_name[0])
                        zone_pod_map[zone] = nlist
                               
          pod_list = "\n".join(item for item in pod_list)
          c_services_data.add_row([f"{o_name}", f"{o_nspace}",f"{o_type}",f"{pod_list}",f"{deploy.status.replicas}", f"{deploy.status.ready_replicas}", f"{zone_pod_map}","Amazing"])
       except Exception as e:
           print(f"Exception {e} occurred")
    elif o_type == "StatefulSet":
       try:        
          stateful = apps_api.read_namespaced_stateful_set(name=o_name, namespace=o_nspace)        
        
          pod_list = list()
          zone_pod_map = dict()
          for i in range(stateful.status.replicas):
              pname = o_name + f"-{i}"
              pod_data = core_api.read_namespaced_pod(name=pname, namespace=o_nspace)         
              if pod_data is not None:
                pod_list.append(pod_data.metadata.name)           
                node_name = find_hostname(pod_data.status.host_ip)
                if node_name[0] is not None:
                   zone = zone_lookup(node_name[0])
                   if zone not in zone_pod_map.keys():
                     nlist = list()                    
                     nlist.append(node_name[0])
                     zone_pod_map[zone] = nlist                        
                   else:
                     nlist = zone_pod_map[zone]
                     nlist.append(node_name[0])
                     zone_pod_map[zone] = nlist                                                    
          pod_list = "\n".join(item for item in pod_list)
          c_services_data.add_row([f"{o_name}", f"{o_nspace}", f"{o_type}",f"{pod_list}",f"{stateful.status.replicas}", f"{stateful.status.ready_replicas}", f"{zone_pod_map}","Amazing"])
       except Exception as e:
           print(f"Exception {e} occurred")          
    elif o_type == "DaemonSet":
       try:                
         daemon = apps_api.read_namespaced_daemon_set(name=o_name, namespace=o_nspace)
         if daemon is not None:
             l_selector = daemon.spec.selector.match_labels
             for k,v in l_selector.items():
                 selector_l = f"{k}={v}"
             
             pod_for_daemon = core_api.list_namespaced_pod(namespace=o_nspace, label_selector=f"{selector_l}")
             if pod_for_daemon is not None:
                 pod_list = list()
                 zone_pod_map = dict()
                 for pod in pod_for_daemon.items:
                     pod_list.append(pod.metadata.name)
                     node_name = find_hostname(pod.status.host_ip)
                     if node_name[0] is not None:
                         zone = zone_lookup(node_name[0])
                         if zone not in zone_pod_map.keys():
                           nlist = list()
                           nlist.append(node_name[0])
                           zone_pod_map[zone] = nlist                        
                         else:
                           nlist = zone_pod_map[zone]
                           nlist.append(node_name[0])
                           zone_pod_map[zone] = nlist
                                
             pod_list = "\n".join(item for item in pod_list)
             c_services_data.add_row([f"{o_name}", f"{o_nspace}",f"{o_type}",f"{pod_list}",f"{daemon.status.desired_number_scheduled}", f"{daemon.status.number_available}", f"{zone_pod_map}","Amazing"])            
       except Exception as e:
           print(f"Exception {e} occurred")                 
    else:
        print("Invalid Object type")
        sys.exit(1)
    

def find_zones() -> int:
    """Find all zones the cluster and print details of the nodes in each zone
    
    returns: number of zones found on the system
    """
    core_api= client.CoreV1Api()
    global zone_node_map
    l_selector = "topology.kubernetes.io/zone"
    node_list = core_api.list_node(label_selector=l_selector)
    total_nodes = len(node_list.items)
   
    for node in node_list.items:
        if node.metadata.labels is not None:
            for l,v in node.metadata.labels.items():
                if l == l_selector:
                  if v not in zone_node_map:
                      zlist = list()
                      zlist.append(node.metadata.name)
                      zone_node_map[v] = zlist
                  else:
                      nlist = zone_node_map[v]
                      nlist.append(node.metadata.name)
                      zone_node_map[v] = nlist    

    zone_table = PrettyTable(header=False, hrules=ALL)
    zone_table.align = "l"
    zone_table.add_row(["Total Zones:", str(len(zone_node_map.keys()))])
    zone_table.add_row(["Total Nodes across zones:", total_nodes])
    for zone,nodes in zone_node_map.items():
        n_list = ",".join(item for item in nodes)
        zone_table.add_row([f"Nodes in {zone}:", f"{n_list}"])

    print(zone_table)    
    
    return len(zone_node_map.keys())


def read_service_data_and_generate_report(nspace, cmap):
    """Read the configmap and generate a report for distribution
    """    
    core_api= client.CoreV1Api()    
    namespace = nspace
    name = cmap
    configmap = core_api.read_namespaced_config_map(name=name, namespace=namespace)
    if type(configmap.data) == dict:
        for key, val in configmap.data.items():
            service_dict = ast.literal_eval(val)
            if type(service_dict["critical-services"]) is dict:
               for k, v in service_dict["critical-services"].items():
                   object_name = k
                   nspace = v["namespace"]
                   replicas = v["replicas"]
                   object_type = v["type"]
                   check_distribution_and_report(object_name, nspace, replicas, object_type)    


"""Script to get Pods for a specific service and report distribution across zones
"""
if __name__ == "__main__":
    cmap = sys.argv[1] #configmap which has the resiliency config
    nspace = sys.argv[2] # namspace for the configmap    
    config.load_kube_config()
    if find_zones() > 0:
       read_service_data_and_generate_report(nspace, cmap)
       print(c_services_data)