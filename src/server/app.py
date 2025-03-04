from flask import Flask, jsonify, request
from models.zoneList import get_zones
from models.zoneDescribe import describe_zone
from models.criticalServiceList import get_critical_service_list
from models.criticalServiceDescribe import describe_service
from models.criticalServiceUpdate import update_critical_services
app = Flask(__name__)

@app.route("/zones", methods=["GET"])
def listZones():
    return get_zones()

@app.route('/zones/<zone_name>', methods=['GET'])
def desc_zone(zone_name):
    return describe_zone(zone_name)

@app.route('/criticalservices', methods=['GET'])
def listCriticalService():
    return get_critical_service_list()

@app.route("/criticalservices/<service_name>", methods=["GET"])
def describeCriticalService(service_name):
    return describe_service(service_name)

@app.route("/criticalservices", methods=["PATCH"])
def updateCriticalService():
    new_data = request.get_json()
    return update_critical_services(new_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
