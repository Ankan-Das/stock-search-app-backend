from flask import Flask, request, jsonify
from extensions import db, bcrypt
from sqlalchemy.pool import QueuePool

from models import User
from flask_cors import CORS
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import auth, credentials, firestore

def create_app():
    # Load environment variables
    load_dotenv()

    ## Firebase Settings
    cred = credentials.Certificate('app/mystocksfirebaseapp-firebase-adminsdk-1fh4a-60b9a9cbe8.json')
    firebase_admin.initialize_app(cred)
    firestoreDB = firestore.client()

    # Get allowed origins from environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                                            'pool_size': 5,  # Number of connections to keep in the pool
                                            'max_overflow': 10,  # Additional connections allowed beyond the pool size
                                            'pool_timeout': 30,  # Timeout in seconds before giving up on getting a connection
                                            'pool_recycle': 1800  # Recycle connections after 1800 seconds (30 minutes) to prevent idle issues
                                        }
    # app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Secret key for JWT

    db.init_app(app)
    # jwt.init_app(app)
    bcrypt.init_app(app)

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

    # Register Blueprints (example)
    from .routes.value_routes import value_routes
    from .routes.stock_routes import stock_routes
    from .routes.credential_routes import credential_blurprint

    # app.register_blueprint(value_routes, url_prefix="/api/values")
    # app.register_blueprint(stock_routes, url_prefix="/api/stocks")
    # app.register_blueprint(credential_blurprint, url_prefix="/api/auth")

    @app.route('/register', methods=['POST'])
    def register():
        try:
            data = request.json
            email = data['email']
            password = data['password']
            role = data['role']

            print(email)

            userRecord = auth.create_user(email=email, password=password)

            print("HERE 1")

            userData = {
                'user_id': email.split("@")[0],
                'uid': userRecord.uid,
                'role': role
            }
            print("HERE 2")
            firestoreDB.collection('users').document(userData['user_id']).set(userData)
            print("HERE 3")
            return jsonify({
                "message": "registration successful",
                "userId": userData['user_id']
                }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return app
