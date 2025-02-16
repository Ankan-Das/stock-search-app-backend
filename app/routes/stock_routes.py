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
        price = int(data['price'])

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


@stock_routes.route('/get_stocks', methods=['GET'])
def get_stocks():
    """
    Fetch all available stocks.
    """
    try:
        stocks = Stock.query.all()
        stocks_data = [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "price": 105006.0  # Placeholder for current price, replace with real-time data if available
            } for stock in stocks
        ]
        return jsonify({"stocks": stocks_data}), 200
    except Exception as e:
        return jsonify({"error": "An error occurred while fetching stocks", "details": str(e)}), 500


@stock_routes.route('/get_transactions', methods=['GET'])
def get_transactions():
    """
    Fetches all transactions for a given user.
    """
    
    user_id = request.args.get('user_id')
    try:
        # Validate if user exists
        user = User.query.filter_by(username=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        print(user.id)
        # Fetch all transactions for the user
        transactions = (db.session.query(Transaction, Stock.symbol)
                        .join(Stock, Transaction.stock_id == Stock.id)
                        .filter(Transaction.user_id == user.id)
                        .order_by(Transaction.created_at.desc())
                        .all())

        if not transactions:
            return jsonify({"error": "No transactions found for the user"}), 404
        
        transactions_data = [
            {
                "transaction_id": txn.Transaction.id,
                "symbol": txn.symbol,  # Get stock symbol instead of stock_id
                "transaction_type": txn.Transaction.transaction_type,
                "units": txn.Transaction.units,
                "price": txn.Transaction.price,
                "created_at": txn.Transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for txn in transactions
        ]

        return jsonify({"transactions": transactions_data}), 200
    
    except Exception as e:
        return jsonify({"error": "An error occurred while fetching transactions", "details": str(e)}), 500
