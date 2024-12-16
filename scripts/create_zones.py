import subprocess
import json

# To label the kubernetes nodes with the topology zoning
def label_nodes(node, rack_id):
    result = subprocess.run(
            ["kubectl", "label", "node", f"{node}", f"topology.kubernetes.io/zone=rack-{rack_id}", "--overwrite"],
            stdout=subprocess.PIPE
            )

# To get the rack to node mapping details by executing "rack_to_node_mapping.py"
try:
    result = subprocess.run(["python3", "rack_to_node_mapping.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
    #result = subprocess.run(["python3", "rack_to_node_mapping_testing.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)

except subprocess.CalledProcessError as e:
    print(f"Error occurred while running kubectl: {e.stderr}")
    exit(1)
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    exit(1)

rack_info = result.stdout
rack_info = json.loads(rack_info)
rack_id = 0

# To traverse the nodes in the rack and assign them the labels
for sublist in rack_info.values():
    rack_id += 1
    for item in sublist:
        if not item.startswith("ncn-s"):
            print(f"Node {item} is going to be placed on zone-{rack_id}")
            label_nodes(item, rack_id)
