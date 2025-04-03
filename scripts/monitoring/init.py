from kubernetes import client, config
import yaml
from datetime import datetime
import logging
import json
import lib_configmap
import re
import lib_rms

config.load_kube_config()  # Or use load_incluster_config() if running inside a Kubernetes pod
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

namespace = 'rack-resiliency'
dynamic_cm = 'rrs-mon-dynamic'

def zone_discovery():
    #mount and run rack_to_node_mapping.py in final cut
    with open('rack_mapping.json', 'r') as file:
        contents = file.read()
        logger.info(f"Rack placement from discovery script is : \n {contents}")
        placement = json.loads(contents)
    
    pattern = re.compile(r"^ncn-(m|w)\d{3}$")

    updated_k8s_data = {
        rack: [
            {"name": item, "Status": lib_rms.get_node_status(item)} 
            for item in nodes if pattern.match(item)
        ]
        for rack, nodes in placement.items()
    }
            
    updated_ceph_data, ceph_healthy_status = lib_rms.get_ceph_status()
    
    #return json.dumps(updated_data, indent=2)        
    return updated_k8s_data, updated_ceph_data    

def init():
    configmap_data = lib_configmap.get_configmap(namespace, dynamic_cm)

    try:        
        yaml_content = configmap_data.get('dynamic-data.yaml', None)
        if yaml_content:
            dynamic_data = yaml.safe_load(yaml_content)    
        else:
            logger.error("No content found under dynamic-data.yaml in rrs-mon-dynamic configmap")
            exit(1)

        #update init timestamp in rrs-dynamic configmap
        timestamps = dynamic_data.get('timestamps', {})
        init_timestamp = timestamps.get('init_timestamp', None)
        if not init_timestamp:
            timestamps['init_timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            lib_configmap.update_configmap_data(namespace, dynamic_cm, configmap_data, 'dynamic-data.yaml', yaml.dump(dynamic_data, default_flow_style=False))
            logger.info(f"Updated init_timestamp in rrs-dynamic configmap")
        else:
            logger.debug("Init time already present in configmap")
            logger.info(f"Reinitializing Rack Resiliency Service. This could happen if previous RRS pod is died")
        
        #Retrieve k8s and CEPH node/zone information and update in rrs-dynamic configmap
        zone_info = dynamic_data.get('zone')
        logger.info(f"Retrieving zone information and status of k8s and CEPH nodes")
        updated_k8s_data, updated_ceph_data = zone_discovery()
        #print(zone_info)
        zone_info['k8s_zones_with_nodes'] = updated_k8s_data
        zone_info['ceph_zones_with_nodes'] = updated_ceph_data
        #print(zone_info)
        logger.info(f"Updating zone information in rrs-dynamic configmap")
        lib_configmap.update_configmap_data(namespace, dynamic_cm, configmap_data, 'dynamic-data.yaml', yaml.dump(dynamic_data, default_flow_style=False))

    except KeyError as e:
        logger.error(f"KeyError: Missing expected key in the configmap data - {e}")
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")            

        #Read critical services					
        #Read timers for loops					
        #Record which node and Rack I am running in dynamic configmap
        
if __name__ == "__main__":
    init()