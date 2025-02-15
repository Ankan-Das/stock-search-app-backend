from extensions import db
from datetime import datetime

# Define the User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, email=None):
        self.username = username
        self.email = email


class LatestUserID(db.Model):
    __tablename__ = 'latest_user_id'
    id = db.Column(db.Integer, primary_key=True)
    latest_id = db.Column(db.Integer, nullable=False, default=0)


# Define the Stock model
class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(9), unique=True, nullable=False)  # 9-digit unique stock ID
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)

    def __init__(self, stock_id, symbol, name):
        self.stock_id = stock_id
        self.symbol = symbol
        self.name = name

# Define the Portfolio model
class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    units = db.Column(db.Integer, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, stock_id, units, average_buy_price):
        self.user_id = user_id
        self.stock_id = stock_id
        self.units = units
        self.average_buy_price = average_buy_price

# Define the Transaction model
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    units = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, stock_id, transaction_type, units, price):
        self.user_id = user_id
        self.stock_id = stock_id
        self.transaction_type = transaction_type
        self.units = units
        self.price = price
