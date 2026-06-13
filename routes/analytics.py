from flask import Blueprint, jsonify
from database.db import db
from models.customer import Customer
from models.order import Order
from models.campaign import Campaign
from models.communication import Communication, AIRecommendation
import json

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/dashboard', methods=['GET'])
def get_dashboard_summary():
    """
    Returns high-level KPI card metrics for the Executive Dashboard.
    """
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_campaigns = Campaign.query.count()
    
    # Calculate communication counts
    sent_count = Communication.query.count()
    delivered_count = Communication.query.filter(Communication.status != 'Failed', Communication.status != 'Sent').count()
    opened_count = Communication.query.filter(Communication.status.in_(['Opened', 'Read', 'Clicked'])).count()
    clicked_count = Communication.query.filter(Communication.status == 'Clicked').count()
    
    # Total revenue influenced is the sum of all campaigns' revenue_generated
    revenue_influenced = db.session.query(db.func.sum(Campaign.revenue_generated)).scalar() or 0.0
    
    # Potential revenue opportunity is calculated from active recommendations
    recs = AIRecommendation.query.filter_by(status='Active').all()
    potential_revenue = 0.0
    for r in recs:
        try:
            metrics_dict = json.loads(r.metrics) if r.metrics else {}
            potential_revenue += metrics_dict.get('recoverable_revenue', metrics_dict.get('revenue_potential', 0.0))
        except Exception:
            continue
            
    # Quick campaign list for dashboard
    recent_campaigns = Campaign.query.order_by(Campaign.created_date.desc()).limit(5).all()
    
    return jsonify({
        'kpi': {
            'total_customers': total_customers,
            'total_orders': total_orders,
            'total_campaigns': total_campaigns,
            'messages_sent': sent_count,
            'messages_delivered': delivered_count,
            'messages_opened': opened_count,
            'messages_clicked': clicked_count,
            'revenue_influenced': round(revenue_influenced, 2),
            'potential_revenue_opportunity': round(potential_revenue, 2)
        },
        'recent_campaigns': [c.to_dict() for c in recent_campaigns]
    })

@analytics_bp.route('/api/analytics', methods=['GET'])
def get_detailed_analytics():
    """
    Compiles detailed charts data (Funnels, Channel Breakdown, and Trends).
    """
    # 1. Performance rates across all sent messages
    total_sent = Communication.query.count()
    total_delivered = Communication.query.filter(Communication.status != 'Failed', Communication.status != 'Sent').count()
    total_opened = Communication.query.filter(Communication.status.in_(['Opened', 'Read', 'Clicked'])).count()
    total_clicked = Communication.query.filter(Communication.status == 'Clicked').count()
    total_failed = Communication.query.filter_by(status='Failed').count()
    
    global_delivery_rate = round((total_delivered / total_sent) * 100, 1) if total_sent > 0 else 0.0
    global_open_rate = round((total_opened / total_delivered) * 100, 1) if total_delivered > 0 else 0.0
    global_click_rate = round((total_clicked / total_opened) * 100, 1) if total_opened > 0 else 0.0
    
    # 2. Campaign Funnel data
    funnel = [
        {'stage': 'Targeted (Sent)', 'count': total_sent, 'percentage': 100},
        {'stage': 'Delivered', 'count': total_delivered, 'percentage': round((total_delivered / total_sent) * 100, 1) if total_sent > 0 else 0},
        {'stage': 'Opened', 'count': total_opened, 'percentage': round((total_opened / total_sent) * 100, 1) if total_sent > 0 else 0},
        {'stage': 'Clicked', 'count': total_clicked, 'percentage': round((total_clicked / total_sent) * 100, 1) if total_sent > 0 else 0}
    ]
    
    # 3. Channel Performance Breakdown
    channels = ["WhatsApp", "SMS", "Email", "RCS"]
    channel_performance = []
    
    for channel in channels:
        sent = Communication.query.filter_by(channel=channel).count()
        delivered = Communication.query.filter(Communication.channel == channel, Communication.status != 'Failed', Communication.status != 'Sent').count()
        opened = Communication.query.filter(Communication.channel == channel, Communication.status.in_(['Opened', 'Read', 'Clicked'])).count()
        clicked = Communication.query.filter(Communication.channel == channel, Communication.status == 'Clicked').count()
        revenue = db.session.query(db.func.sum(Campaign.revenue_generated)).filter(Campaign.channel == channel).scalar() or 0.0
        
        channel_performance.append({
            'channel': channel,
            'sent': sent,
            'delivered_rate': round((delivered / sent) * 100, 1) if sent > 0 else 0.0,
            'open_rate': round((opened / delivered) * 100, 1) if delivered > 0 else 0.0,
            'click_rate': round((clicked / opened) * 100, 1) if opened > 0 else 0.0,
            'revenue': round(revenue, 2)
        })
        
    # 4. Campaign Performance Trend (grouped by last 10 completed campaigns)
    trend_campaigns = Campaign.query.filter(Campaign.status == 'Completed').order_by(Campaign.created_date.desc()).limit(8).all()
    # Reverse so they are in chronological order
    trend_campaigns.reverse()
    
    campaign_trend = []
    for c in trend_campaigns:
        campaign_trend.append({
            'name': c.name.split(' - ')[-1][:20], # Truncate long names
            'open_rate': c.open_rate,
            'click_rate': c.click_rate,
            'revenue': c.revenue_generated
        })
        
    # 5. Customer Growth Trend (grouped by city for variety, or simulated months)
    # Let's show Customer distribution by City as a bar chart
    cities = db.session.query(Customer.city, db.func.count(Customer.id)).group_by(Customer.city).all()
    city_distribution = [{'city': city, 'customers': count} for city, count in cities]
    
    # Churn Risk segmentation count
    low_risk = Customer.query.filter(Customer.risk_score < 0.4).count()
    med_risk = Customer.query.filter(Customer.risk_score >= 0.4, Customer.risk_score < 0.75).count()
    high_risk = Customer.query.filter(Customer.risk_score >= 0.75).count()
    
    risk_distribution = [
        {'name': 'Low Risk', 'value': low_risk},
        {'name': 'Medium Risk', 'value': med_risk},
        {'name': 'High Churn Risk', 'value': high_risk}
    ]
    
    return jsonify({
        'rates': {
            'delivery_rate': global_delivery_rate,
            'open_rate': global_open_rate,
            'click_rate': global_click_rate,
            'failed_count': total_failed
        },
        'funnel': funnel,
        'channel_performance': channel_performance,
        'campaign_trend': campaign_trend,
        'city_distribution': city_distribution,
        'risk_distribution': risk_distribution
    })
