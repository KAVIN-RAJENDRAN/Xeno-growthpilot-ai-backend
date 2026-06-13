from datetime import datetime
from database.db import db

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    lifetime_spend = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    last_purchase_date = db.Column(db.DateTime, nullable=True)
    clv = db.Column(db.Float, default=0.0)
    risk_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Active') # Active, At Risk, Churned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True, cascade="all, delete-orphan")
    communications = db.relationship('Communication', backref='customer', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'city': self.city,
            'gender': self.gender,
            'age': self.age,
            'lifetime_spend': self.lifetime_spend,
            'total_orders': self.total_orders,
            'last_purchase_date': self.last_purchase_date.strftime('%Y-%m-%d %H:%M:%S') if self.last_purchase_date else None,
            'clv': self.clv,
            'risk_score': self.risk_score,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
