from flask import Flask, request, jsonify, Response
from extensions import db, bcrypt
from sqlalchemy.pool import QueuePool

from models import User
from flask_cors import CORS
from flask_migrate import Migrate
import os
import json
from dotenv import load_dotenv
import pprint

import firebase_admin
from firebase_admin import auth, credentials, firestore

from flask_sock import Sock

def create_app():
    # Load environment variables
    load_dotenv()

    ## Firebase Settings
    firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    
    with open(firebase_credentials_path, "r") as f:
        firebase_credentials = json.load(f)

    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)
    firestoreDB = firestore.client()

    # Get allowed origins from environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

    app = Flask(__name__)

    sock = Sock(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                                            'pool_size': 5,  # Number of connections to keep in the pool
                                            'max_overflow': 10,  # Additional connections allowed beyond the pool size
                                            'pool_timeout': 30,  # Timeout in seconds before giving up on getting a connection
                                            'pool_recycle': 1800  # Recycle connections after 1800 seconds (30 minutes) to prevent idle issues
                                        }
    
    db.init_app(app)

    # print("Migrating ...")
    # migrate = Migrate(app, db)
    # print("Migrating Done!")

    # Configure CORS with dynamic origins
    CORS(app, resources={r"*": {"origins": allowed_origins.split(",")}}, supports_credentials=True)

    # # Ensure tables are created within the app context
    # print("Creating tables")
    # with app.app_context():
    #     db.create_all()
    # print("Tables created")

    ### ~~~~~~~~~~~~~~~~~~~~~~~~~ TESTING TWELVE DATA LIBRARY ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    import time
    from twelvedata import TDClient
    import threading

    td = TDClient(apikey="b98b47709df24df0909b3af1f59b55e0")

    # Track client subscriptions
    client_subscriptions = {}
    current_data = {}

    def start_twelvedata_ws():
        def on_event(event):
            if event['event'] in {"subscribe-status", "heartbeat"}:
                return
            symbol = event.get('symbol')
            price = event.get('price')
            if symbol and price:
                current_data[symbol] = price  # Store latest prices globally
            print("current data", current_data, "\n")

        while True:
            try:
                print("Connecting to Twelvedata WebSocket...")
                ws = td.websocket(
                    symbols=",".join(["EUR/USD", "AAPL", "BTC/USD", "INFY"]),
                    on_event=on_event
                )
                ws.connect()
                print("Twelvedata WebSocket connected")
                while True:
                    ws.heartbeat()
                    time.sleep(5)
            except Exception as e:
                print(f"Twelvedata WebSocket error: {e}")
                time.sleep(5)

    @app.route('/update-subscription', methods=['POST'])
    def update_subscription():
        client_id = request.remote_addr
        data = request.json
        symbols = data.get("symbols", [])
        client_subscriptions[client_id] = symbols

        print("Client subscriptions", client_subscriptions)
        
        return {"status": "success", "subscribed_symbols": symbols}, 200

    @app.route('/stock-updates')
    def stock_updates():
        # Capture `remote_addr` outside the generator
        client_id = request.remote_addr

        def stream():
            while True:
                print("CLIENT SUBS: ", client_subscriptions)
                print("CURRENT DATA: ", current_data)
                symbols = client_subscriptions.get(client_id, [])
                updates = [
                    {"symbol": symbol, "price": current_data.get(symbol, "Loading...")}
                    for symbol in symbols
                ]
                yield f"data: {json.dumps(updates)}\n\n"
                time.sleep(1)  # Push updates every second

        return Response(stream(), content_type='text/event-stream')


    # Start Twelvedata WebSocket in a separate thread
    threading.Thread(target=start_twelvedata_ws, daemon=True).start()
    
    ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




    # Register Blueprints (example)
    # from .routes.value_routes import value_routes
    from .routes.stock_routes import stock_routes

    # app.register_blueprint(value_routes, url_prefix="/api/values")
    app.register_blueprint(stock_routes, url_prefix="/api/stocks")

    @app.route('/register', methods=['POST'])
    def register():
        try:
            data = request.json
            email = data['email']
            password = data['password']
            role = data['role']

            userRecord = auth.create_user(email=email, password=password)

            userData = {
                'user_id': email.split("@")[0],
                'uid': userRecord.uid,
                'role': role
            }
            firestoreDB.collection('users').document(userData['user_id']).set(userData)
            return jsonify({
                "message": "registration successful",
                "userId": userData['user_id']
                }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        

    @app.route('/ping', methods=['POST'])
    def ping():
        return jsonify({
            "message": "Ping successful, server is up now!"
        }), 200

    return app
