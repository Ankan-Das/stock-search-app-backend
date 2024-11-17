# backend/app/routes/stock_routes.py
from flask import Blueprint, request, jsonify, make_response

stock_routes = Blueprint("stock_routes", __name__)

@stock_routes.route("/buy-stock", methods=["OPTIONS", "POST"])
def buy_stock():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = 'https://stock-search-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    data = request.json
    symbol = data.get("symbol")
    price = data.get("price")
    action = data.get("action")

    if not symbol or not price:
        return jsonify({"success": False, "message": "Invalid input"}), 400

    # Simulate a buy action
    return jsonify({"success": True, "message": f"Bought {symbol} at {price}."})

@stock_routes.route("/sell-stock", methods=["OPTIONS", "POST"])
def sell_stock():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = 'https://stock-search-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    data = request.json
    symbol = data.get("symbol")
    price = data.get("price")
    action = data.get("action")

    if not symbol or not price:
        return jsonify({"success": False, "message": "Invalid input"}), 400

    # Simulate a sell action
    return jsonify({"success": True, "message": f"Sold {symbol} at {price}."})
