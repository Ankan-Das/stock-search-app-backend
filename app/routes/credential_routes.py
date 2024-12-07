from extensions import db, bcrypt
from models import User

from flask import Blueprint, request, jsonify
from datetime import datetime
from config import Config

credential_blurprint = Blueprint('auth', __name__)


@credential_blurprint.route('/register', methods=['POST'])
def register():
    data = request.json
    password = data.get('password')
    confirm_password = data.get('confirmPassword')
    role = data.get('role', 'user')

    if not (password and confirm_password):
        return jsonify({"message": "All fields are required"}), 400
    
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create a new user instance
    new_user = User(password=hashed_password, role=role)

    try:
        # Add and commit the new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Return the success message with the generated user_id
        return jsonify({
            "message": "registration successful",
            "userId": new_user.user_id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Error occurred while creating user",
            "error": str(e)
        }), 500

    

@credential_blurprint.route('/login', methods=['POST'])
def login():
    data = request.json
    print(data)
    user_id = data.get('userId')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({
            "message": "user_id and password are required"
        }), 400
    
    # Find user by user_id
    user = User.query.filter_by(user_id=user_id).first()

    if user and bcrypt.check_password_hash(user.password, password):
        # Create the JWT token with user_id and role
        access_token = create_access_token(identity=user.user_id, additional_claims={"role": user.role})
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "role": user.role,
        }), 200

    return jsonify({
        "message": "Invalid user_id or password"
    }), 401