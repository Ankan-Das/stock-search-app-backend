from flask import Flask, request, jsonify, Response
from models import db
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

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    #                                         'pool_size': 5,  # Number of connections to keep in the pool
    #                                         'max_overflow': 10,  # Additional connections allowed beyond the pool size
    #                                         'pool_timeout': 30,  # Timeout in seconds before giving up on getting a connection
    #                                         'pool_recycle': 1800  # Recycle connections after 1800 seconds (30 minutes) to prevent idle issues
    #                                     }
    
    db.init_app(app)



    print("Migrating ...")
    migrate = Migrate(app, db)
    print("Migrating Done!")

    # Configure CORS with dynamic origins
    CORS(app, resources={r"*": {"origins": allowed_origins.split(",")}}, supports_credentials=True)

    # Ensure tables are created within the app context
    print("Creating tables")
    with app.app_context():
        db.create_all()
    print("Tables created")

    ### ~~~~~~~~~~~~~~~~~~~~~~~~~ TESTING TRUE DATA LIBRARY ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    import time
    import websocket
    import threading
    # Track client subscriptions (ideally use a shared store like Redis in production)
    client_subscriptions = {}
    # Store the latest prices for symbols received from TrueData
    current_data = {}
    market_status = {}
    _map = {"100000737": "ITC", "100011226": "ITCHOTELS", "100001262": "RELIANCE", "100004843": "DELHIVERY", "100000025": "ADANIENT", "100000027": "ADANIGREEN"}

    def start_truedata_ws():
        def on_message(ws, message):
            print("Received message:", message)
            try:
                data = json.loads(message)
                # If the message contains market status (e.g. NSE_EQ), update market_status
                if "NSE_EQ" in data:
                    global market_status
                    market_status = data
                    print("\n\n\nUpdated market status:", market_status)
                elif "trade" in data:
                    _data = data['trade']
                    # Otherwise, assume it's a price update for a symbol.
                    symbol = _map.get(_data[0])
                    price = _data[2]
                    if symbol and price:
                        current_data[symbol] = price  # update the latest price
                    print("\nUpdated current data:", current_data, "\n")
            except Exception as e:
                print("Error parsing message:", e)

        def on_error(ws, error):
            print("TrueData WS error:", error)

        def on_close(ws, close_status_code, close_msg):
            print("TrueData WS closed:", close_status_code, close_msg)

        def on_open(ws):
            print("TrueData WS connected")
            # Send the initial subscription message.
            subscription_msg = {
                "method": "addsymbol",
                "symbols": ["ITC", "ITCHOTELS", "RELIANCE", "DELHIVERY", "ADANIENT", "ADANIGREEN"]
            }
            ws.send(json.dumps(subscription_msg))
            print("Subscription message sent:", subscription_msg)
            
            # Define a function to send market status request every 5 minutes.
            def send_market_status():
                try:
                    status_msg = {"method": "getmarketstatus"}
                    ws.send(json.dumps(status_msg))
                    print("Sent market status request:", status_msg)
                except Exception as e:
                    print("Error sending market status:", e)
                # Schedule the next market status request in 300 seconds (5 minutes)
                threading.Timer(5, send_market_status).start()
            
            # Start the recurring market status request
            send_market_status()

        while True:
            try:
                print("Connecting to TrueData WebSocket...")
                ws = websocket.WebSocketApp(
                    "wss://push.truedata.in:8086?user=Trial153&password=ankan153",
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever()
            except Exception as e:
                print("Exception in TrueData WS connection:", e)
            time.sleep(5)

    @app.route('/update-subscription', methods=['POST'])
    def update_subscription():
        client_id = request.remote_addr
        data = request.json
        symbols = data.get("symbols", [])
        client_subscriptions[client_id] = symbols

        print("Client subscriptions", client_subscriptions)
        # Return the subscription details.
        return {"status": "success", "subscribed_symbols": symbols}, 200

    @app.route('/stock-updates')
    def stock_updates():
        # Capture client's IP outside of the streaming generator.
        client_id = request.remote_addr

        def stream():
            while True:
                symbols = client_subscriptions.get(client_id, [])
                # Build price updates for the symbols the client is subscribed to.
                print("CURRENT DATA HERE: ", current_data)
                price_updates = [
                    {"symbol": symbol, "price": current_data.get(symbol, "Loing...")}
                    for symbol in symbols
                ]
                # Combine the price updates with the latest market status.
                updates = {
                    "prices": price_updates,
                    "market_status": market_status
                }
                yield f"data: {json.dumps(updates)}\n\n"
                time.sleep(1)  # Push updates every second

        return Response(stream(), content_type='text/event-stream')
    
    threading.Thread(target=start_truedata_ws, daemon=True).start()
        
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
            print("USER CREATED IN FIREBASE AUTH")

            userData = {
                'user_id': email.split("@")[0],
                'uid': userRecord.uid,
                'role': role
            }
            firestoreDB.collection('users').document(userData['user_id']).set(userData)
            print("USER ADDED in FIREBASE COLLECTION")

            ## If the role is user, update it in the DB
            username = email.split("@")[0]
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({"error": "Username already exists"}), 400
            print("NOT EXISTING USER")
            
            if role=="user":
                new_user = User(username=username, email=email)
                try:
                    db.session.add(new_user)
                    db.session.commit()
                    return jsonify({"message": "User created successfully", "user_id": new_user.id}), 201
                except Exception as e:
                    db.session.rollback()
                    return jsonify({"error": "An error occurred while creating the user", "details": str(e)}), 500

            return jsonify({
                "message": "registration successful",
                "userId": userData['user_id']
                }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        

    @app.route('/ping', methods=['GET'])
    def ping():
        return jsonify({
            "message": "Ping successful, server is up now!"
        }), 200

    return app
