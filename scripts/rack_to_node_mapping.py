import requests
import json
import subprocess
from collections import defaultdict
import base64

# Define the endpoint URL
hsm_url = "https://api-gw-service-nmn.local/apis/smd/hsm/v2/State/Components"
sls_url= "https://api-gw-service-nmn.local/apis/sls/v1/search/hardware"

# Run the kubectl command to get the secret 
try:
    result = subprocess.run(
        ["kubectl", "get", "secrets", "admin-client-auth", "-o", "jsonpath={.data.client-secret}"],
        stdout=subprocess.PIPE,  # Capture stdout
        stderr=subprocess.PIPE,  # Capture stderr
        universal_newlines=True,  # Use text mode for output decoding
        check=True,  # Will raise an exception if the command fails
    )
    # If the command was successful, result will be a CompletedProcess object
    client_secret = base64.b64decode(result.stdout.strip()).decode('utf-8')

except subprocess.CalledProcessError as e:
    print(f"Error occurred while running kubectl: {e.stderr}")
    exit(1)
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    exit(1)

# Set up the parameters and URL to make the POST request
url = "https://api-gw-service-nmn.local/keycloak/realms/shasta/protocol/openid-connect/token"
data = {
    "grant_type": "client_credentials",
    "client_id": "admin-client",
    "client_secret": f"{client_secret}",
}

# Make the API request to get the token
response = requests.post(url, data=data)

# Print the json output
token = response.json()
token = token.get("access_token")

# Parameters for sls 
params = {'type': 'comptype_node'}
headers = {
    "Authorization": f"Bearer {token}",  # Add the token as a Bearer token
    "Accept": "application/json"         # Indicate you want a JSON response
}

# Make the GET request
hsm_response = requests.get(hsm_url, headers=headers)
sls_response = requests.get(sls_url, headers=headers, params=params)

hsm_data = hsm_response.json()
sls_data = sls_response.json()

# Check the response status and print the JSON output
if hsm_response.status_code == 200:
    filtered_data = [component for component in hsm_data["Components"] if component.get("Role") == "Management" and component.get("SubRole") == "Master" or component.get("SubRole") == "Worker" or component.get("SubRole") == "Storage"]

    # Group by rack ID (extracted from "ID")
    res_rack = defaultdict(list)

    for component in filtered_data:
        rack_id = component["ID"].split("c")[0]  # Extract "x3000" from "x3000c0s1b75n75"
        for sls_entry in sls_data:
            if sls_entry["Xname"] == component["ID"]:
                aliases = sls_entry["ExtraProperties"]["Aliases"][0]
                res_rack[rack_id].append(aliases)
    res_rack = json.dumps(res_rack, indent=4)
    #res_rack = res_rack.replace('"', '')
    print(res_rack)
else:
    print(f"Failed to access the endpoint. Status code: {response.status_code}")
    print("Response text:", response.text)
