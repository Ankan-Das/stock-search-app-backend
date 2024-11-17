# backend/app/routes/value_routes.py
from flask import Blueprint, request, jsonify, make_response

value_routes = Blueprint("value_routes", __name__)

# In-memory storage for simplicity
values = {"maxLoss": None, "totalAmount": None}

@value_routes.route("/get-values", methods=["OPTIONS", "GET"])
def get_values():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = 'https://stock-search-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    return jsonify(values)

@value_routes.route("/set-values", methods=["OPTIONS","POST"])
def set_values():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = 'https://stock-search-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    data = request.json
    max_loss = data.get("maxLoss")
    total_amount = data.get("totalAmount")

    if max_loss is not None:
        values["maxLoss"] = max_loss

    if total_amount is not None:
        values["totalAmount"] = total_amount

    return jsonify({"success": True, "maxLoss": values["maxLoss"], "totalAmount": values["totalAmount"]})
