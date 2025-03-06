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

from flask import jsonify
from resources.criticalServices import get_configmap

def get_critical_services():
    """Fetch and format critical services grouped by namespace in the required structure."""
    try:
        services = get_configmap().get("critical-services", {})
        result = {"namespace": {}}
        for name, details in services.items():
            namespace = details["namespace"]
            if namespace not in result["namespace"]:
                result["namespace"][namespace] = []
            result["namespace"][namespace].append({
                "name": name,
                "type": details["type"]
            })

        return result
    except Exception as e:
        return {"error": str(e)}

def get_critical_service_list():
    """Returning the response in JSON Format"""
    return jsonify({"critical-services": get_critical_services()})

