import datetime

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'  # Update if using another DB
    SECRET_KEY = 'your_secret_key_here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TOKEN_EXPIRATION = datetime.timedelta(hours=1)  # Token valid for 1 hour
    SESSION_COOKIE_SECURE = True      # For HTTPS only
    SESSION_COOKIE_SAMESITE = 'None'
