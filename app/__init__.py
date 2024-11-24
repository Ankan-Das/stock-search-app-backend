from flask import Flask, request, jsonify
from extensions import db, jwt, bcrypt
from models import User
from flask_cors import CORS
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

def create_app():
    # Load environment variables
    load_dotenv()


    # Get allowed origins from environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Secret key for JWT

    db.init_app(app)
    jwt.init_app(app)
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

    app.register_blueprint(value_routes, url_prefix="/api/values")
    app.register_blueprint(stock_routes, url_prefix="/api/stocks")
    app.register_blueprint(credential_blurprint, url_prefix="/api/auth")

    @app.route('/register', methods=['POST'])
    def register():
       data = request.json
       return jsonify({
           "message": "registration successful",
           "userId": "1234"
           }), 200

    return app
