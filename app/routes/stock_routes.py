# backend/app/routes/stock_routes.py
from flask import Blueprint, request, jsonify, make_response
from app import db
from models import User, Stock, Transaction, Portfolio

stock_routes = Blueprint("stock_routes", __name__)

@stock_routes.route('/trade', methods=['POST'])
def trade_stock():
    """
    Handles the 'buy' and 'sell' functionality for a user to trade a stock.
    Expects JSON input with user_id, stock_id, transaction_type (buy/sell), units, and price.
    """
    try:
        # Parse request data
        data = request.get_json()
        required_fields = ['user_id', 'stock_id', 'transaction_type', 'units', 'price']

        # Check for missing required fields
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400

        user_id = data['user_id']
        stock_id = data['stock_id']
        transaction_type = data['transaction_type'].lower()
        units = data['units']
        price = data['price']

        # Validate the user
        user = User.query.filter_by(username=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Validate the stock
        stock = Stock.query.filter_by(symbol=stock_id).first()
        if not stock:
            return jsonify({"error": "Stock not found"}), 404

        # Validate transaction type
        if transaction_type not in ['buy', 'sell']:
            return jsonify({"error": "Invalid transaction type. Must be 'buy' or 'sell'"}), 400

        # Handle 'buy' transaction
        if transaction_type == 'buy':
            # Add the transaction to the Transactions table
            transaction = Transaction(
                user_id=user.id,
                stock_id=stock.id,
                transaction_type='buy',
                units=units,
                price=price
            )
            db.session.add(transaction)

            # Update the user's portfolio
            portfolio_entry = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
            if portfolio_entry:
                # If the stock already exists in the portfolio, update it
                total_cost = portfolio_entry.units * portfolio_entry.average_buy_price
                total_cost += units * price
                portfolio_entry.units += units
                portfolio_entry.average_buy_price = total_cost / portfolio_entry.units
            else:
                # If the stock is not in the portfolio, create a new entry
                portfolio_entry = Portfolio(
                    user_id=user.id,
                    stock_id=stock.id,
                    units=units,
                    average_buy_price=price
                )
                db.session.add(portfolio_entry)

        # Handle 'sell' transaction
        elif transaction_type == 'sell':
            # Check if the stock exists in the user's portfolio
            portfolio_entry = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
            if not portfolio_entry or portfolio_entry.units < units:
                return jsonify({"error": "Insufficient stock units in the portfolio to sell"}), 400

            # Add the transaction to the Transactions table
            transaction = Transaction(
                user_id=user.id,
                stock_id=stock.id,
                transaction_type='sell',
                units=units,
                price=price
            )
            db.session.add(transaction)

            # Update the portfolio
            portfolio_entry.units -= units
            if portfolio_entry.units == 0:
                db.session.delete(portfolio_entry)  # Remove entry if no units left

        # Commit changes to the database
        db.session.commit()

        return jsonify({"message": f"Stock {transaction_type} transaction completed successfully"}), 201

    except Exception as e:
        # Rollback in case of an error
        db.session.rollback()
        return jsonify({"error": "An error occurred while processing the transaction", "details": str(e)}), 500


@stock_routes.route('/get_portfolio', methods=['GET'])
def get_portfolio():
    """
    Fetches the portfolio for a given user.
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = 'https://stock-search-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    user_id = request.args.get('user_id')
    try:
        # Check if valid user
        user = User.query.filter_by(username=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        portfolio = Portfolio.query.filter_by(user_id=user.id).all()
        
        if not portfolio:
            return jsonify({"error": "No portfolio found for the user"}), 404

        portfolio_data = [
            {
                "stock_id": Stock.query.get(entry.stock_id).symbol,
                "units": entry.units,
                "average_buy_price": entry.average_buy_price,
            } for entry in portfolio
        ]

        return jsonify({"portfolio": portfolio_data}), 200
    except Exception as e:
        return jsonify({"error": "An error occurred while fetching the portfolio", "details": str(e)}), 500
