from flask import Flask
from models.zoneList import get_zones
from models.zoneDescribe import describe_zone

app = Flask(__name__)

@app.route("/zones", methods=["GET"])
def listZones():
    return get_zones()

@app.route('/zones/<zone_name>', methods=['GET'])
def desc_zone(zone_name):
    return describe_zone(zone_name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
