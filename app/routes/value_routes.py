# backend/app/routes/value_routes.py
from flask import Blueprint, request, jsonify

value_routes = Blueprint("value_routes", __name__)

# In-memory storage for simplicity
values = {"maxLoss": None, "totalAmount": None}

@value_routes.route("/get-values", methods=["GET"])
def get_values():
    return jsonify(values)

@value_routes.route("/set-values", methods=["POST"])
def set_values():
    data = request.json
    max_loss = data.get("maxLoss")
    total_amount = data.get("totalAmount")

    if max_loss is not None:
        values["maxLoss"] = max_loss

    if total_amount is not None:
        values["totalAmount"] = total_amount

    return jsonify({"success": True, "maxLoss": values["maxLoss"], "totalAmount": values["totalAmount"]})
