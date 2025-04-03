import subprocess
import base64
import json
import sys
import check_zones

# To check the enablement of rack resiliency feature flag
def check_rr_enablement():
    # Run kubectl command and capture JSON output
    namespace = "loftsman"
    secret_name = "site-init"

    kubectl_cmd = ["kubectl", "-n", namespace, "get", "secret", secret_name, "-o", "json"]
    kubectl_output = subprocess.run(kubectl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)

    # Parse JSON output
    secret_data = json.loads(kubectl_output.stdout)

    # Extract and decode the base64 data
    encoded_yaml = secret_data["data"]["customizations.yaml"]
    decoded_yaml = base64.b64decode(encoded_yaml).decode("utf-8")

    # Write the yaml output to a file
    output_file = "/tmp/customizations.yaml"
    with open(output_file, "w") as f:
        f.write(decoded_yaml)

    print(f"Decoded YAML saved to {output_file}")

    # Define the key path
    output_file = "/tmp/customizations1.yaml"
    key_path = "spec.kubernetes.services.rack-resiliency.enabled"

    # Run yq command to extract the value
    yq_cmd = ["yq", "r", output_file, key_path]
    result = subprocess.run(yq_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)

    # Extract and clean the output
    rr_check = result.stdout.strip()

    print(f"Rack Resiliency Enabled: {rr_check}")
    return rr_check

def check_zoning():
    print("Checking Zoning for k8s and ceph nodes")
    check_zones.main()

check = check_rr_enablement()
if check == "true":
    print("RR flag is enabled in the site-init secret")
    check_zoning()
    # Add the helm chart deployment script here
else:
    print("RR flag is disabled in the site-init secret. Not deploying the RRS chart")
    sys.exit(1)
