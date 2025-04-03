#!/usr/bin/python3
#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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

import threading
import time
import json
import yaml
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from kubernetes import client, config
from concurrent.futures import ThreadPoolExecutor
import requests
import sys
import base64
import copy
import lib_configmap
import lib_rms


app = Flask(__name__)
# Load kube config from local environment (use in local or non-cluster environments)
config.load_kube_config()  # Or use load_incluster_config() if running inside a Kubernetes pod
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

logging.basicConfig(
    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',  # Include thread name in logs
    level=logging.INFO
)
logger = logging.getLogger()

executor = ThreadPoolExecutor(max_workers=10)
# Global Lock for monitor_critical_services
monitor_lock = threading.Lock()
is_monitor_running = False           
namespace = 'rack-resiliency'
#dynamic_cm = 'dynamic-sravani-test'
#static_cm = 'static-sravani-test'
dynamic_cm = 'rrs-mon-dynamic'
static_cm = 'rrs-mon-static'

def update_zone_status():
    logger.info("Getting latest status for zones and nodes")
    dynamic_cm_data = lib_configmap.get_configmap(namespace, dynamic_cm)
    
    try:
        yaml_content = dynamic_cm_data.get('dynamic-data.yaml', None)
        #print(yaml_content)
        if yaml_content:
            dynamic_data = yaml.safe_load(yaml_content)    
        else:
            logger.error("No content found under dynamic-data.yaml in rrs-mon-dynamic configmap")
            exit(1)
        
        zone_info = dynamic_data.get('zone')
        k8s_info = zone_info.get('k8s_zones_with_nodes')
        k8s_info_old = copy.deepcopy(k8s_info)
    
        for zone, nodes in k8s_info.items():
            for node in nodes:
                node['Status'] = lib_rms.get_node_status(node['name'])
                
        zone_info['k8s_zones_with_nodes'] = k8s_info

        ceph_info_old = zone_info.get('ceph_zones_with_nodes')
        updated_ceph_data, ceph_healthy_status = lib_rms.get_ceph_status()
        zone_info['ceph_zones_with_nodes'] = updated_ceph_data

        if k8s_info_old != k8s_info or ceph_info_old != updated_ceph_data:
            logger.info(f"Updating zone information in rrs-dynamic configmap")
            lib_configmap.update_configmap_data(namespace, dynamic_cm, dynamic_cm_data, 'dynamic-data.yaml', yaml.dump(dynamic_data, default_flow_style=False))        
        return k8s_info, updated_ceph_data, ceph_healthy_status

    except KeyError as e:
        logger.error(f"Key error occurred: {e}")
        logger.error("Ensure that 'zone' and 'k8s_zones_with_nodes' keys are present in the dynamic configmap data.")
    except yaml.YAMLError as e:
        logger.error(f"YAML error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def update_critical_services(reloading=False):
    static_cm_data = lib_configmap.get_configmap(namespace, static_cm)
    dynamic_cm_data = lib_configmap.get_configmap(namespace, dynamic_cm)
    
    try:
        if reloading:
            logger.info('Retrieving critical services information from rrs-static configmap')
            json_content = static_cm_data.get('critical-service-config.json', None)
        else:
            logger.info('Retrieving critical services information from rrs-dynamic configmap')
            json_content = dynamic_cm_data.get('critical-service-config.json', None)
        if json_content:
            services_data = json.loads(json_content)    
        else:
            logger.error("No content found under critical-service-config.json in rrs-mon configmap")
            exit(1)

        updated_services = lib_rms.get_critical_services_status(services_data)
        #print(updated_services)
        services_json = json.dumps(updated_services, indent=2)
        print(services_json)
        if services_json != dynamic_cm_data.get('critical-service-config.json', None):
            logger.debug('critical services are modified. Updating dynamic configmap with latest information')
            lib_configmap.update_configmap_data(namespace, dynamic_cm, dynamic_cm_data, 'critical-service-config.json', services_json)
        return services_json
    except json.JSONDecodeError:
        logger.error("Failed to decode critical-service-config.json from configmap")
        return
    except KeyError as e:
        logger.error(f"KeyError occurred: {str(e)} - Check if the configmap contains the expected keys")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
    


def monitoring_loop():
    """Initiate monitoring critical services and CEPH"""
    global is_monitor_running
    with monitor_lock:
        if is_monitor_running:
            logger.error(f"Thread {threading.current_thread().name} cannot run monitoring because it's already running")
            return  # Return early if the function is already running
        is_monitor_running = True 

    logger.info('Monitoring critical services and zone status...')
    
    # Read the 'rrs-mon' configmap and parse the data
    static_cm_data = lib_configmap.get_configmap(namespace, static_cm)
    monitoring_timeout = static_cm_data.get('monitoring-timeout', 300)  # Default 15 minutes if not found
    timer = 0
    while timer < monitoring_timeout:
        #Retrieve and update critical services status 
        latest_services_json = update_critical_services()
        #Retrieve and update k8s/CEPH status and CEPH health
        latest_k8_info, latest_ceph_info, ceph_healthy_status = update_zone_status()

        timer += 60
        time.sleep(60)  # Sleep for 60 seconds before checking again

    logger.info(f"Ending the monitoring loop after {monitoring_timeout} seconds")
    unrecovered_services = []
    for service, details in json.loads(latest_services_json)["critical-services"].items():
        if details["status"] == "PartiallyConfigured" or details["balanced"] == "false":
            unrecovered_services.append(service)
    if unrecovered_services:
        logger.error(f"Services {unrecovered_services} are still not recovered even after {monitoring_timeout} seconds")

    if ceph_healthy_status == False:
        logger.error(f"CEPH is still not healthy even after {monitoring_timeout} seconds")

    with monitor_lock:
        is_monitor_running = False  # Reset the flag when the function is done


def token_fetch():
    try:
        secret = v1.read_namespaced_secret("admin-client-auth", "default")
        client_secret = base64.b64decode(secret.data['client-secret']).decode("utf-8")
        #logger.debug(f"Client Secret: {client_secret}")

        keycloak_url = "https://api-gw-service-nmn.local/keycloak/realms/shasta/protocol/openid-connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": "admin-client",
            "client_secret": f"{client_secret}",
        }
        response = requests.post(keycloak_url, data=data)
        token = response.json()
        token = token.get("access_token")
        return token
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"Failed to parse JSON: {e}")
        exit(1)
    except Exception as err:
        logger.error("Error collecting secret from Kubernetes: {}".format(err))
        exit(1)
    
                
        
def check_failure_type(component_xname):
    """Check if it is a rack or node failure"""
    logger.info("Checking failure type i.e., node or rack failure upon recieving SCN ...")
    token = token_fetch()
    
    #hsm_url = "http://cray-smd.services.svc.cluster.local/hsm/v2/State/Components"
    hsm_url = "https://api-gw-service-nmn.local/apis/smd/hsm/v2/State/Components"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }    
    try:
        # Make the GET request to hsm endpoint
        hsm_response = requests.get(hsm_url, headers=headers)
        hsm_response.raise_for_status()
        hsm_data = hsm_response.json()   

        valid_subroles = {"Master", "Worker", "Storage"}
        filtered_data = [
            component for component in hsm_data.get("Components", [])
            if component.get("Role") == "Management" and component.get("SubRole") in valid_subroles
        ]

        for component in filtered_data:
            if component["ID"] == component_xname:
                rack_id = component["ID"].split("c")[0]  # Extract "x3000" from "x3000c0s1b75n75"
                break

        # Extract the components with ID starting with rack_id
        rack_components = [
            {"ID": component["ID"], "State": component["State"]}
            #for component in hsm_data["Components"]
            for component in filtered_data
            if component["ID"].startswith(rack_id)
        ]
        
        rack_failure = True
        for component in rack_components:
            if component['State'] in ['On', 'Ready','Populated']:
                rack_failure = False
            print(f"ID: {component['ID']}, State: {component['State']}")
        if rack_failure:
            logger.info("All the components in the rack are not healthy. It is a RACK FAILURE")
        else:
            logger.info("Not all the components present in the rack are down. It is only a NODE FAILURE")

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"Failed to parse JSON: {e}")
        exit(1)


@app.route("/scn", methods=["POST"])
def handleSCN():
    """Handle incoming POST requests and initiate monitoring"""
    logger.info("POST call received from HMNFD")

    # Get JSON data from request
    try:
        notification_json = request.get_json()
        logger.info("JSON data received: %s", notification_json)

        # Extract components and state
        components = notification_json.get('Components', [])
        state = notification_json.get('State', '')

        if not components or not state:
            logger.error("Missing 'Components' or 'State' in the request")
            return jsonify({"error": "Missing 'Components' or 'State' in the request"}), 400

        # Process the state
        if state == 'Off':
            for component in components:
                logger.info(f'Node {component} is turned Off')
            # Start monitoring services in a new thread
            #print(f"Number of active threads are: {threading.active_count()}")
            
            check_failure_type(component)
            threading.Thread(target=monitoring_loop).start()

            #logger.info(f"Thread {threading.current_thread().name} has ended")
                
        elif state == 'On':
            #print(f"Number of active threads are: {threading.active_count()}")
            for component in components:
                logger.info(f'Node {component} is turned On')
            # Handle cleanup or other actions here if needed

        else:
            logger.warning(f"Unexpected state '{state}' received for {components}.")

        return jsonify({"message": "POST call received"}), 200

    except Exception as e:
        logger.error("Error processing the request: %s", e)
        return jsonify({"error": "Internal server error."}), 500


            
def get_management_xnames():
    """Get xnames for all the management nodes from HSM"""
    logger.info("Getting xnames for all the management nodes from HSM ...")
    token = token_fetch()
    #hsm_url = "http://cray-smd.services.svc.cluster.local/hsm/v2/State/Components"
    hsm_url = "https://api-gw-service-nmn.local/apis/smd/hsm/v2/State/Components"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }   
    try:
        # Make the GET request to hsm endpoint
        hsm_response = requests.get(hsm_url, headers=headers)
        hsm_response.raise_for_status()
        hsm_data = hsm_response.json()
        
        # Filter components with the given role and subroles
        valid_subroles = {"Master", "Worker", "Storage"}
        filtered_data = [
            component for component in hsm_data.get("Components", [])
            if component.get("Role") == "Management" and component.get("SubRole") in valid_subroles
        ]
        
        management_xnames = {component['ID'] for component in filtered_data}
        logger.info(list(management_xnames))
        return list(management_xnames)
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        exit(1)
    except ValueError as e:
        print(f"Failed to parse JSON: {e}")
        exit(1)


def check_and_create_hmnfd_subscription(node_ip = ''):
    """Create a subscription entry in hmnfd to recieve SCNs(state change notification) for the management components"""
    logger.info("Checking HMNFD subscription for SCN notifications ...")
    token = token_fetch()
    #subscriber_node = 'rack-resiliency'
    subscriber_node = 'x3000c0s1b0n0'
    agent_name = 'rms'
    
    # URL for in mesh pod-to-pod communication
    #get_url = f"http://cray-hmnfd.services.svc.cluster.local/hmi/v2/subscriptions" 
    #post_url = f"http://cray-hmnfd.services.svc.cluster.local/hmi/v2/subscriptions/{subscriber_node}/agents/{agent_name}" 
    
    get_url = "https://api-gw-service-nmn.local/apis/hmnfd/hmi/v2/subscriptions"
    post_url = f"https://api-gw-service-nmn.local/apis/hmnfd/hmi/v2/subscriptions/{subscriber_node}/agents/{agent_name}"

    subscribing_components = get_management_xnames()
    #print(subscribing_components)
    post_data = {
        "Components": subscribing_components,
        "Roles": ["Management"],
        "States": ["Ready","on","off","empty","unknown","populated"],
        "Url": "http://10.102.193.27:3000/scn"
    } 
    headers = {
        "Authorization": f"Bearer {token}",        
        "Accept": "application/json"
    }

    try:
        get_response = requests.get(get_url, headers=headers)
        #print("Done with get request")
        data = get_response.json()
        exists = any("rms" in subscription['Subscriber'] for subscription in data['SubscriptionList'])

        if not exists:
            logger.info(f"rms not present in the HMNFD subscription list, creating it ...")
            #print(post_data)
            post_response = requests.post(post_url, json=post_data, headers=headers)
            post_response.raise_for_status()
            logger.info(f"Successfully subscribed to hmnfd for SCN notifications")
            #logger.info(f"Response data: {post_response.json()}")
        else:
            logger.info(f"rms is already present in the subscription list")
    except requests.exceptions.RequestException as e:
        # Handle request errors (e.g., network issues, timeouts, non-2xx status codes)
        logger.error(f"Failed to make subscription request to hmnfd. Error: {e}")
        #print(f"Response content: {post_response.content}")
        #exit(1)
    except ValueError as e:
        # Handle JSON parsing errors
        logger.error(f"Failed to parse JSON response: {e}")
        #exit(1)

def initial_check_and_update():
     
    dynamic_cm_data = lib_configmap.get_configmap(namespace, dynamic_cm)   
    try:
        yaml_content = dynamic_cm_data.get('dynamic-data.yaml', None)
        if yaml_content:
            dynamic_data = yaml.safe_load(yaml_content)    
        else:
            logger.error("No content found under dynamic-data.yaml in rrs-mon-dynamic configmap")
            exit(1)

        #Update RMS start timestamp in dynamic configmap
        timestamps = dynamic_data.get('timestamps', {})
        rms_start_timestamp = timestamps.get('start_timestamp_rms', None)
        if not rms_start_timestamp:
            timestamps['start_timestamp_rms'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            lib_configmap.update_configmap_data(namespace, dynamic_cm, dynamic_cm_data, 'dynamic-data.yaml', yaml.dump(dynamic_data, default_flow_style=False))
            logger.debug(f"Updated rms_start_timestamp in rrs-dynamic configmap")
        else:
            logger.debug("RMS start time already present in configmap")
            logger.info(f"Rack Resiliency Monitoring Service is restarted because of a failure")  

    except ValueError as e:
        logger.error(f"Error during configuration check and update: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)
        

def run_flask():
    """Run the Flask app in a separate thread for listening to HMNFD notifications"""
    logger.info(f"Running flask on 3000 port on localhost to recieve notifications from HMNFD")
    #app.config['ENV'] = 'production'
    #app.config['DEBUG'] = False
    #app.logger.setLevel(logging.ERROR)
        #node_ip = subprocess.check_output(["hostname", "-i"]).decode("utf-8").strip()
    app.run(host="0.0.0.0", port=3000, threaded=True, debug=False, use_reloader=False)

    

if __name__ == "__main__":
  
    initial_check_and_update()
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    time.sleep(1)

    while True:
        logger.info("starting the loop")
        check_and_create_hmnfd_subscription()
        update_critical_services(True)
        update_zone_status()
        #break
        time.sleep(300)  #update it to 600 after demo