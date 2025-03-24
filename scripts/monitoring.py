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
import logging
from flask import Flask, request, jsonify
from kubernetes import client, config
from concurrent.futures import ThreadPoolExecutor
import requests
import subprocess
from collections import defaultdict
import sys
import base64
import re

app = Flask(__name__)
# Load kube config from local environment (use in local or non-cluster environments)
config.load_kube_config()  # Or use load_incluster_config() if running inside a Kubernetes pod
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

logging.basicConfig(
    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',  # Include thread name in logs
    level=logging.INFO
)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=10)
# Global Lock for monitor_critical_services
monitor_lock = threading.Lock()
is_monitor_running = False

def get_service_status(service_name, service_namespace, service_type):
    """Helper function to fetch service status based on service type."""
    try:
        if service_type == 'Deployment':
            app = apps_v1.read_namespaced_deployment(service_name, service_namespace)
            return app.status.replicas, app.status.ready_replicas
        elif service_type == 'StatefulSet':
            app = apps_v1.read_namespaced_stateful_set(service_name, service_namespace)
            return app.status.replicas, app.status.ready_replicas
        elif service_type == 'DaemonSet':
            app = apps_v1.read_namespaced_daemon_set(service_name, service_namespace)
            return app.status.desired_number_scheduled, app.status.number_ready
        else:
            logger.warning(f"Unsupported service type: {service_type}")
            return None, None
    except client.exceptions.ApiException as e:
        match = re.search(r'Reason: (.*?)\n', str(e))
        if match:
            error_message = match.group(1)     
        logger.error(f"Error fetching {service_type} {service_name}: {error_message}")
        return None, None


def monitor_critical_services(critical_services):
    """Monitor critical services based on configuration from the configmap."""
    for service_name, service_details in critical_services.items():
        service_namespace = service_details.get('namespace')  
        service_type = service_details.get('type')

        # Get the status of the service (desired vs. ready replicas)
        desired_replicas, ready_replicas = get_service_status(service_name, service_namespace, service_type)

        imbalanced_services = []
        # If replicas data was returned
        if desired_replicas is not None and ready_replicas is not None:
            if ready_replicas < desired_replicas:
                imbalanced_services.append(service_name)
                logger.warning(f"{service_type} '{service_name}' in namespace '{service_namespace}' is not ready. "
                               f"Only {ready_replicas} replicas are ready out of {desired_replicas} desired replicas.")
            
            else:
                logger.debug(f"Desired replicas and ready replicas are matching for '{service_name}'")
    logger.warning(f"List of imbalanced services are - {imbalanced_services}")

def run_command(command):
    """Helper function to run a command and return the result."""
    logger.debug(f"Running command: {command}")
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Command {command} errored out with : {e.stderr}")
    return result.stdout

def monitor_ceph():
    """Monitor CEPH status and log the results"""
    logger.info('Monitoring CEPH...')
    host = 'ncn-m001'
    #command = f"ssh {host} 'ceph orch host ls -f json'"
    ceph_hosts = json.loads(run_command("ceph orch host ls -f json"))
    #command = f"ssh {host} 'ceph -s -f json'"
    ceph_status = json.loads(run_command("ceph -s -f json"))
    
    failed_hosts = []
    for host in ceph_hosts:
        if host["status"] not in ["", "online"]:
            failed_hosts.append(host["hostname"])
            logger.warning(f"Host {host['hostname']} is in - {host['status']} state")
    
    if failed_hosts:
        logger.warning(f"{len(failed_hosts)} out of {len(ceph_hosts)} ceph nodes are not healthy")


    health_status = ceph_status.get("health", {}).get("status", "UNKNOWN")
    #print(health_status)
    
    if "HEALTH_OK" not in health_status:
        logger.warning("CEPH is not healthy")
        pg_degraded_message = ceph_status.get("health", {}).get("checks", {}).get("PG_DEGRADED", {}).get("summary", {}).get("message", "")
        
        if "Degraded" in pg_degraded_message:
            if 'recovering_objects_per_sec' or 'recovering_bytes_per_sec' in data.get('pgmap', {}):
                logger.info(f"CEPH recovery is in progress...")
            else:
                logger.warning("CEPH PGs are in degraded state, but recovery is not happening")
    else:
        logger.info("CEPH is healthy")
    
    ceph_services = json.loads(run_command("ceph orch ps -f json"))
    #print(ceph_services)
    failed_services = []
    for service in ceph_services:
        if service["status_desc"] != "running":
            failed_services.append(service["service_name"])
            logger.warning(f"Service {service['service_name']} running on {service['hostname']} is in {service['status_desc']} state")
        else:
            logger.debug(f"Service {service['service_name']} running on {service['hostname']} is in {service['status_desc']} state")
    if failed_services:
        logger.warning(f"{len(failed_services)} out of {len(ceph_services)} ceph services are not running")                


def monitoring_loop():
    """Initiate monitoring critical services and CEPH"""
    global is_monitor_running
    with monitor_lock:
        if is_monitor_running:
            logger.error(f"Thread {threading.current_thread().name} cannot run func because it's already running.")
            return  # Return early if the function is already running
        is_monitor_running = True 

    logger.info('Monitoring critical services...')
    
    # Read the 'rrs-mon' configmap and parse the data
    configmap = v1.read_namespaced_config_map('rrs-mon-static', 'rack-resiliency')
    configmap_data = configmap.data
    try:
        json_data = json.loads(configmap_data.get('critical-service-config.json'))
    except json.JSONDecodeError:
        logger.error("Failed to decode critical-service-config.json from configmap.")
        return

    monitoring_timeout = json_data.get('monitoring-timeout', 900)  # Default 15 minutes if not found
    critical_services = json_data.get('critical-services', {})
    logger.info(f'Number of critical services to monitor: {len(critical_services)}')

    timer = 0
    while timer < monitoring_timeout:
        monitor_critical_services(critical_services)
        monitor_ceph()
        timer += 60
        time.sleep(60)  # Sleep for 60 seconds before checking again

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
        sys.exit(1)
    
                
        
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
            logger.info("Starting monitoring_loop in a new thread")
            threading.Thread(target=monitoring_loop).start()

            logger.info(f"Thread {threading.current_thread().name} has ended")
                
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


def create_hmnfd_subscription(node_ip):
    """Create a subscription entry in hmnfd to recieve SCNs(state change notification) for the management components"""
    logger.info("Creating HMNFD subscription for SCN notifications ...")
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
        print("Done with get request")
        data = get_response.json()
        exists = any("rms" in subscription['Subscriber'] for subscription in data['SubscriptionList'])

        if not exists:
            logger.info(f"rms not present in the subscription list, creating it ...")
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
        print(f"Response content: {post_response.content}")
        exit(1)
    except ValueError as e:
        # Handle JSON parsing errors
        logger.error(f"Failed to parse JSON response: {e}")
        exit(1)



def run_flask():
    """Run the Flask app in a separate thread."""
    logger.info(f"Running flask on 3000 port on localhost to recieve notifications from HMNFD")
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.logger.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=3000, threaded=True, debug=False, use_reloader=False)
    

if __name__ == "__main__":
    #node_ip = subprocess.check_output(["hostname", "-i"]).decode("utf-8").strip()
    node_ip = "0.0.0.0"
    # Start Flask app in a separate thread
    create_hmnfd_subscription(node_ip) 
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
      
    
    
    #get_management_xnames()
    #check_failure_type("x3000c0s26b0n0")
    #monitoring_loop()
    ####initial_monitor()