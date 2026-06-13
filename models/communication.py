from datetime import datetime
from database.db import db
import json

class Communication(db.Model):
    __tablename__ = 'communications'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    channel = db.Column(db.String(20), nullable=False) # WhatsApp, SMS, Email, RCS
    status = db.Column(db.String(20), default='Sent') # Sent, Delivered, Failed, Opened, Read, Clicked
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    clicked_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(250), nullable=True)

    # Relationships
    events = db.relationship('CommunicationEvent', backref='communication', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'campaign_id': self.campaign_id,
            'channel': self.channel,
            'status': self.status,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S') if self.sent_at else None,
            'delivered_at': self.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if self.delivered_at else None,
            'opened_at': self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else None,
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None,
            'clicked_at': self.clicked_at.strftime('%Y-%m-%d %H:%M:%S') if self.clicked_at else None,
            'error_message': self.error_message
        }

class CommunicationEvent(db.Model):
    __tablename__ = 'communication_events'
    
    id = db.Column(db.Integer, primary_key=True)
    communication_id = db.Column(db.Integer, db.ForeignKey('communications.id'), nullable=False)
    event_type = db.Column(db.String(20), nullable=False) # Sent, Delivered, Failed, Opened, Read, Clicked
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'communication_id': self.communication_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

class Segment(db.Model):
    __tablename__ = 'segments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    criteria = db.Column(db.String(250), nullable=False)
    customer_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'criteria': self.criteria,
            'customer_count': self.customer_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class AIRecommendation(db.Model):
    __tablename__ = 'ai_recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # Churn Prevention, Engagement, Upsell
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    metrics = db.Column(db.Text, nullable=True) # JSON stored as String
    recommended_action = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), default='Active') # Active, Applied, Dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        try:
            metrics_dict = json.loads(self.metrics) if self.metrics else {}
        except Exception:
            metrics_dict = {}
            
        return {
            'id': self.id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'metrics': metrics_dict,
            'recommended_action': self.recommended_action,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
