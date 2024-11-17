from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

def create_app():
    # Load environment variables
    load_dotenv()

    # Get allowed origins from environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

    app = Flask(__name__)

    # Configure CORS with dynamic origins
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Register Blueprints (example)
    from .routes.value_routes import value_routes
    from .routes.stock_routes import stock_routes

    app.register_blueprint(value_routes, url_prefix="/api/values")
    app.register_blueprint(stock_routes, url_prefix="/api/stocks")

    return app
