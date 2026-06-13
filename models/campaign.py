from datetime import datetime
from database.db import db

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    goal = db.Column(db.Text, nullable=False)
    audience_size = db.Column(db.Integer, default=0)
    channel = db.Column(db.String(20), nullable=False) # WhatsApp, SMS, Email, RCS
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Draft') # Draft, Scheduled, Running, Completed, Failed
    delivery_rate = db.Column(db.Float, default=0.0)
    open_rate = db.Column(db.Float, default=0.0)
    click_rate = db.Column(db.Float, default=0.0)
    revenue_generated = db.Column(db.Float, default=0.0)
    message_template = db.Column(db.Text, nullable=True)

    # Relationships
    communications = db.relationship('Communication', backref='campaign', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'goal': self.goal,
            'audience_size': self.audience_size,
            'channel': self.channel,
            'created_date': self.created_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'delivery_rate': self.delivery_rate,
            'open_rate': self.open_rate,
            'click_rate': self.click_rate,
            'revenue_generated': self.revenue_generated,
            'message_template': self.message_template
        }
