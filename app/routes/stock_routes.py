# backend/app/routes/stock_routes.py
from flask import Blueprint, request, jsonify

stock_routes = Blueprint("stock_routes", __name__)

@stock_routes.route("/buy-stock", methods=["POST"])
def buy_stock():
    data = request.json
    symbol = data.get("symbol")
    price = data.get("price")
    action = data.get("action")

    if not symbol or not price:
        return jsonify({"success": False, "message": "Invalid input"}), 400

    # Simulate a buy action
    return jsonify({"success": True, "message": f"Bought {symbol} at {price}."})

@stock_routes.route("/sell-stock", methods=["POST"])
def sell_stock():
    data = request.json
    symbol = data.get("symbol")
    price = data.get("price")
    action = data.get("action")

    if not symbol or not price:
        return jsonify({"success": False, "message": "Invalid input"}), 400

    # Simulate a sell action
    return jsonify({"success": True, "message": f"Sold {symbol} at {price}."})
