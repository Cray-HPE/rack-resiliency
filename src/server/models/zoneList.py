from flask import jsonify
from models.zoneUtils import map_zones

# zones_bp = Blueprint('zones', __name__)

# @zones_bp.route('/zones', methods=['GET'])
def get_zones():
    """Endpoint to get summary of all zones."""
    return jsonify(map_zones())
