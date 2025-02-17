from flask import Flask, request, jsonify, Response
from models import db
from sqlalchemy.pool import QueuePool

from models import User, LatestUserID
from flask_cors import CORS
from flask_migrate import Migrate
import os
import json
from dotenv import load_dotenv
import pprint

import firebase_admin
from firebase_admin import auth, credentials, firestore

import threading

# ~~~~~~~~~~~~~~~~~~~~~~~~~ REDIS OPERATIONS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import redis

# Setup Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# Use decode_responses=True to work with native Python strings.
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Helper functions for subscriptions and current data in Redis
def set_client_subscription(client_id, symbols):
    redis_client.set(f"subscription:{client_id}", json.dumps(symbols))

def get_client_subscription(client_id):
    data = redis_client.get(f"subscription:{client_id}")
    if data:
        return json.loads(data)
    return []

def update_current_data(symbol, price):
    redis_client.hset("current_data", symbol, price)

def get_current_price(symbol):
    price = redis_client.hget("current_data", symbol)
    if price is None:
        return "Loading..."
    return price

def update_market_status(status):
    redis_client.set("market_status", json.dumps(status))

def get_market_status():
    status = redis_client.get("market_status")
    if status:
        return status.strip('\"')
    return "CLOSED"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from app.stocks_list import NSE_STOCK, MAP

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


    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = 'https://trade-app-frontend.vercel.app'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        # If you're sending cookies or credentials, include:
        # response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    ### ~~~~~~~~~~~~~~~~~~~~~~~~~ TESTING TRUE DATA LIBRARY ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    import time
    import websocket


    def start_truedata_ws():
        def on_message(ws, message):
            try:
                data = json.loads(message)
                # If the message contains market status (e.g. NSE_EQ), update market_status
                if "NSE_EQ" in data:
                    update_market_status(data["NSE_EQ"])
                # Case where the data arrives for the first time
                elif "symbolsadded" in data:
                    for sym in data["symbollist"]:
                        symbol = sym[0]
                        price = sym[3]
                        update_current_data(symbol, price)
                elif "trade" in data:
                    _data = data['trade']
                    # Assume _data[0] is the key for symbol and _data[2] is the price.
                    symbol = MAP.get(_data[0])
                    price = _data[2]
                    if symbol and price:
                        update_current_data(symbol, price)
                        # For debugging, show the current state from Redis.
                        current_data_snapshot = redis_client.hgetall("current_data")
                        print("\nCURRENT DATA INPUT: ", current_data_snapshot, "\n")
            except Exception as e:
                print("Error parsing message:", e)

        def on_error(ws, error):
            print("--TrueData WS error:", error)

        def on_close(ws, close_status_code, close_msg):
            print("--TrueData WS closed:", close_status_code, close_msg)

        def on_open(ws):
            print("--TrueData WS connected")
            # Send the initial subscription message.
            subscription_msg = {
                "method": "addsymbol",
                "symbols": NSE_STOCK
            }
            ws.send(json.dumps(subscription_msg))
            print("--Subscription message sent:", subscription_msg)
            
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
            
            send_market_status()

        while True:
            try:
                print("Connecting to TrueData WebSocket...")
                ws = websocket.WebSocketApp(
                    "wss://replay.truedata.in:8082?user=tdwsp642&password=ankan@642",
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
        set_client_subscription(client_id, symbols)
        # For debugging, print the stored subscription.
        subscription_stored = get_client_subscription(client_id)
        print("Client subscriptions for", client_id, subscription_stored)
        return {"status": "success", "subscribed_symbols": symbols}, 200

    @app.route('/stock-updates')
    def stock_updates():
        client_id = request.remote_addr

        def stream():
            count = 0
            while True:
                symbols = get_client_subscription(client_id)
                current_data_snapshot = redis_client.hgetall("current_data")
                print("\nCURRENT DATA OUTPUT: ", current_data_snapshot, "\n")
                price_updates = [
                    {"symbol": symbol, "price": get_current_price(symbol)}
                    for symbol in symbols
                ]
                # Send the prices update.
                yield f"data: {json.dumps(price_updates)}\n\n"
                # Every 5 seconds, also send market status.
                if count % 5 == 0:
                    yield f"data: {json.dumps({'market_status': get_market_status()})}\n\n"
                count += 1
                time.sleep(1)
        return Response(stream(), content_type='text/event-stream')
    

    @app.route('/stock-stream')
    def stock_stream():
        # Get the stock ids from query parameter. E.g., ?ids=ITC,RELIANCE
        ids_param = request.args.get('ids')
        if not ids_param:
            return "No stock ids provided", 400

        stock_ids = [sid.strip() for sid in ids_param.split(',') if sid.strip()]
        
        def stream():
            start_time = time.time()
            next_market_time = 5  # send market status every 5 seconds
            while True:
                # Build price updates for the provided stock_ids.
                price_updates = [
                    {"symbol": sid, "price": get_current_price(sid)}
                    for sid in stock_ids
                ]
                # Send the prices event every 2 seconds.
                yield f"event: prices\ndata: {json.dumps(price_updates)}\n\n"
                
                # Check if it's time to send market status event.
                current_elapsed = time.time() - start_time
                if current_elapsed >= next_market_time:
                    yield f"event: market_status\ndata: {json.dumps(get_market_status())}\n\n"
                    next_market_time += 5

                time.sleep(2)

        return Response(stream(), content_type='text/event-stream')

    threading.Thread(target=start_truedata_ws, daemon=True).start()

    ## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Register Blueprints (example)
    # from .routes.value_routes import value_routes
    from .routes.stock_routes import stock_routes

    # app.register_blueprint(value_routes, url_prefix="/api/values")
    app.register_blueprint(stock_routes, url_prefix="/api/stocks")


    def add_child(user_id, child_id):
        """
        Update the relationships document for the given master user_id by adding the child_id.
        If the document does not exist, create it with the child_id in an array.
        """
        try:
            relationships_ref = firestoreDB.collection('relationships').document(user_id)
            doc_snapshot = relationships_ref.get()

            if doc_snapshot.exists:
                # Document exists: use ArrayUnion to add child_id
                relationships_ref.update({
                    'children': firestore.ArrayUnion([{'userId': child_id}])
                })
            else:
                # Document does not exist: create it with an initial children array
                relationships_ref.set({
                    'children': [{'userId': child_id}]
                })
            print(f"Successfully updated relationships for user_id: {user_id}")
        except Exception as e:
            print("Error updating relationships: " + str(e))
            raise e


    @app.route('/register', methods=['POST'])
    def register():
        try:
            data = request.json
            masterID = data['masterID']
            password = data['password']
            firstName = data.get('firstName', '')
            lastName = data.get('lastName', '')

            # Begin a SQL transaction
            with db.session.begin():
                # Retrieve the single row in LatestUserID using a FOR UPDATE lock to avoid race conditions.
                latest = LatestUserID.query.with_for_update().first()
                if not latest:
                    # If no row exists, create one with default latest_id = 0.
                    latest = LatestUserID(latest_id=8)
                    db.session.add(latest)
                    db.session.flush()  # Flush to assign an id

                # Increment the latest id and update the record.
                new_id = latest.latest_id + 1
                latest.latest_id = new_id

                # Use the new_id to generate an email (and username).
                username = f"user-000{str(new_id)}"
                email = f"{username}@stocksapp.com"

                # Check if a user already exists with this username.
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    db.session.rollback()
                    return jsonify({"error": "Username already exists"}), 400

                # If the role is "user", create a new SQL User record.
                new_user = User(username=username, email=email)
                db.session.add(new_user)

                # Commit the SQL transaction.
                # (The LatestUserID update and new user insertion are now final.)
                db.session.commit()

            # Now, outside of the SQL transaction, call external services.
            # Create the user in Firebase Auth.
            userRecord = auth.create_user(email=email, password=password)
            app.logger.info("USER CREATED IN FIREBASE AUTH")

            # Prepare user data for Firestore.
            userData = {
                'user_id': str(username),
                'uid': userRecord.uid,
                'role': "user",
                'firstName': firstName,
                'lastName': lastName
            }
            # Write user data to Firestore.
            firestoreDB.collection('users').document(userData['user_id']).set(userData)
            app.logger.info("USER ADDED in FIREBASE COLLECTION")

            add_child(masterID, username)

            # Return the appropriate response.
            return jsonify({"message": "User created successfully", "userId": new_user.username}), 201

        except Exception as e:
            # If an exception occurs, rollback the transaction (if it hasn't been committed)
            db.session.rollback()
            app.logger.error("Error in /register: " + str(e))
            return jsonify({'error': str(e)}), 500

        

    @app.route('/ping', methods=['GET'])
    def ping():
        return jsonify({
            "message": "Ping successful, server is up now!"
        }), 200

    return app
