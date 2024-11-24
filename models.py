from extensions import db
from sqlalchemy import event

# Define the User model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    password = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.String(10), unique=True, nullable=True)  # Will be set after insert
    role = db.Column(db.String(50), nullable=False, default='user')
    
    def __init__(self, password, role='user'):
        self.password = password
        self.role = role

# Event listener to generate user_id after the record is inserted
@event.listens_for(User, 'after_insert')
def generate_user_id(mapper, connection, target):
    user_id = f"user-{str(target.id).zfill(5)}"  # Format the id with leading zeros
    connection.execute(
        User.__table__.update()
        .where(User.id == target.id)
        .values(user_id=user_id)
    )