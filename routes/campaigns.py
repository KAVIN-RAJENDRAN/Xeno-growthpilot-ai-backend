from flask import Blueprint, request, jsonify
from database.db import db
from models.campaign import Campaign
from models.customer import Customer
from models.communication import Communication, CommunicationEvent
from models.order import Order
from services.gemini_service import GeminiService
from datetime import datetime
import requests
import random

campaigns_bp = Blueprint('campaigns', __name__)

@campaigns_bp.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    campaigns = Campaign.query.order_by(Campaign.created_date.desc()).all()
    return jsonify([c.to_dict() for c in campaigns])

@campaigns_bp.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Pagination for communications log
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    comm_query = Communication.query.filter_by(campaign_id=campaign_id).order_by(Communication.sent_at.desc())
    pagination = comm_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Enhance communication records with customer names and details
    comms_list = []
    for comm in pagination.items:
        cust = Customer.query.get(comm.customer_id)
        comm_dict = comm.to_dict()
        comm_dict['customer_name'] = cust.name if cust else 'Unknown'
        comm_dict['customer_email'] = cust.email if cust else 'Unknown'
        comms_list.append(comm_dict)
        
    # Generate AI insights dynamically for completed campaigns
    ai_insights = GeminiService.generate_campaign_insights(campaign_id)
    
    return jsonify({
        'campaign': campaign.to_dict(),
        'communications': comms_list,
        'total_communications': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'ai_insights': ai_insights
    })

@campaigns_bp.route('/api/campaign/send', methods=['POST'])
def send_campaign():
    """
    Launches a campaign.
    Body: {
      "campaign_id": 1,
      "customer_ids": [1, 2, 3],
      "message_template": "Hey {name}..."
    }
    """
    data = request.json or {}
    campaign_id = data.get('campaign_id')
    customer_ids = data.get('customer_ids', [])
    message_template = data.get('message_template')
    
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404
        
    if not customer_ids:
        # Fallback to get customers based on some criteria if empty
        # For safety, let's say we target a random subset of 100 active customers
        customers = Customer.query.filter(Customer.status == 'Active').limit(100).all()
        customer_ids = [c.id for c in customers]
        
    # Update Campaign
    campaign.audience_size = len(customer_ids)
    campaign.status = 'Running'
    campaign.delivery_rate = 0.0
    campaign.open_rate = 0.0
    campaign.click_rate = 0.0
    campaign.revenue_generated = 0.0
    if message_template:
        campaign.message_template = message_template
        
    # Clear previous communications for this campaign if any
    Communication.query.filter_by(campaign_id=campaign.id).delete()
    db.session.commit()
    
    # Create Communication records (status: Sent)
    messages_payload = []
    now = datetime.utcnow()
    
    for c_id in customer_ids:
        cust = Customer.query.get(c_id)
        if not cust:
            continue
            
        comm = Communication(
            customer_id=cust.id,
            campaign_id=campaign.id,
            channel=campaign.channel,
            status='Sent',
            sent_at=now
        )
        db.session.add(comm)
        db.session.flush() # Populate comm.id
        
        # Add Sent Event
        event = CommunicationEvent(
            communication_id=comm.id,
            event_type='Sent',
            timestamp=now
        )
        db.session.add(event)
        
        # Format message template
        text = campaign.message_template or "Hello"
        formatted_text = text.replace("{name}", cust.name)
        
        messages_payload.append({
            'communication_id': comm.id,
            'name': cust.name,
            'email': cust.email,
            'phone': cust.phone,
            'text': formatted_text
        })
        
    db.session.commit()
    
    # Forward to Channel Simulator Service (port 5001)
    simulator_url = "http://localhost:5001/channel/send"
    payload = {
        'campaign_id': campaign.id,
        'channel': campaign.channel,
        'callback_url': 'http://localhost:5000/api/receipt',
        'messages': messages_payload
    }
    
    simulator_sent = False
    error_msg = ""
    try:
        response = requests.post(simulator_url, json=payload, timeout=5)
        if response.status_code == 200:
            simulator_sent = True
        else:
            error_msg = f"Simulator returned code {response.status_code}"
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to connect to Channel Simulator: {e}")
        
    return jsonify({
        'status': 'Running',
        'campaign_id': campaign.id,
        'audience_size': len(customer_ids),
        'simulator_triggered': simulator_sent,
        'simulator_error': error_msg if not simulator_sent else None
    })

@campaigns_bp.route('/api/receipt', methods=['POST'])
def process_receipt():
    """
    Callback endpoint from Channel Simulator.
    Body: {
      "communication_id": 12,
      "event_type": "Delivered",  # Sent, Delivered, Failed, Opened, Read, Clicked
      "timestamp": "2026-06-13T18:00:00",
      "error_message": null
    }
    """
    data = request.json or {}
    comm_id = data.get('communication_id')
    event_type = data.get('event_type')
    timestamp_str = data.get('timestamp')
    error_message = data.get('error_message')
    
    comm = Communication.query.get(comm_id)
    if not comm:
        return jsonify({'error': 'Communication record not found'}), 404
        
    try:
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            timestamp = datetime.utcnow()
            
    # Check if this event already exists (to avoid duplicates)
    existing_event = CommunicationEvent.query.filter_by(
        communication_id=comm_id, 
        event_type=event_type
    ).first()
    
    if not existing_event:
        # Create Event record
        event = CommunicationEvent(
            communication_id=comm.id,
            event_type=event_type,
            timestamp=timestamp
        )
        db.session.add(event)
        
    # Update Communication model status and timestamps
    if event_type == 'Delivered':
        comm.status = 'Delivered'
        comm.delivered_at = timestamp
    elif event_type == 'Failed':
        comm.status = 'Failed'
        comm.error_message = error_message
    elif event_type == 'Opened':
        comm.status = 'Opened'
        comm.opened_at = timestamp
    elif event_type == 'Read':
        # "Read" is specific to channels like WhatsApp/RCS
        comm.status = 'Read'
        comm.read_at = timestamp
    elif event_type == 'Clicked':
        comm.status = 'Clicked'
        comm.clicked_at = timestamp
        
        # SIMULATE CONVERSION!
        # When a customer clicks, there is a chance they buy something
        # Let's say 25% chance of purchase, to generate realistic revenue in the app
        if random.random() < 0.25:
            cust = Customer.query.get(comm.customer_id)
            if cust:
                purchase_amount = round(random.uniform(500, 4500), 2)
                
                # Create a simulated Order for the customer
                order = Order(
                    customer_id=cust.id,
                    order_date=timestamp,
                    amount=purchase_amount,
                    status='Completed'
                )
                db.session.add(order)
                
                # Update customer spend data
                cust.total_orders += 1
                cust.lifetime_spend += purchase_amount
                cust.last_purchase_date = timestamp
                cust.clv = round(cust.lifetime_spend * 1.5, 2)
                cust.status = 'Active'
                cust.risk_score = round(random.uniform(0.05, 0.35), 2)
                
                # Add to Campaign revenue
                camp = Campaign.query.get(comm.campaign_id)
                if camp:
                    camp.revenue_generated += purchase_amount
                    
    db.session.commit()
    
    # Recalculate Campaign overall performance metrics
    camp = Campaign.query.get(comm.campaign_id)
    if camp:
        total = Communication.query.filter_by(campaign_id=camp.id).count()
        if total > 0:
            delivered = Communication.query.filter(Communication.campaign_id == camp.id, Communication.status != 'Failed', Communication.status != 'Sent').count()
            # Opened includes Opened, Read, and Clicked
            opened = Communication.query.filter(Communication.campaign_id == camp.id, Communication.status.in_(['Opened', 'Read', 'Clicked'])).count()
            clicked = Communication.query.filter(Communication.campaign_id == camp.id, Communication.status == 'Clicked').count()
            failed = Communication.query.filter(Communication.campaign_id == camp.id, Communication.status == 'Failed').count()
            
            camp.delivery_rate = round((delivered / total) * 100, 1)
            camp.open_rate = round((opened / delivered) * 100, 1) if delivered > 0 else 0.0
            camp.click_rate = round((clicked / opened) * 100, 1) if opened > 0 else 0.0
            
            # If all communications are finished (either Clicked, Opened, Read, Failed, or just standard Completed)
            # Mark the campaign status as Completed
            pending = Communication.query.filter(
                Communication.campaign_id == camp.id, 
                Communication.status.in_(['Sent', 'Delivered'])
            ).count()
            
            if pending == 0:
                camp.status = 'Completed'
                
            db.session.commit()
            
    return jsonify({'status': 'processed', 'communication_id': comm_id})
