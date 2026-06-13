from flask import Blueprint, request, jsonify
from database.db import db
from models.communication import Segment, AIRecommendation
from services.gemini_service import GeminiService
from services.recommendation_engine import RecommendationEngine

ai_agent_bp = Blueprint('ai_agent', __name__)

@ai_agent_bp.route('/api/segment/generate', methods=['POST'])
def generate_segment():
    """
    Handles natural language audience segmentation.
    Body: { "query": "Bring back inactive premium customers" }
    """
    data = request.json or {}
    query_text = data.get('query', '').strip()
    
    if not query_text:
        return jsonify({'error': 'Query text is required'}), 400
        
    result = GeminiService.parse_audience_query(query_text)
    
    # Save the generated segment to DB for tracking
    new_segment = Segment(
        name=f"Segment for: '{query_text[:40]}...'",
        criteria=result['criteria'],
        customer_count=result['count']
    )
    db.session.add(new_segment)
    db.session.commit()
    
    result['segment_id'] = new_segment.id
    result['segment_name'] = new_segment.name
    
    return jsonify(result)

@ai_agent_bp.route('/api/campaign/generate', methods=['POST'])
def generate_campaign_templates():
    """
    Generates campaign messages for various channels and tones.
    Body: {
      "goal": "Bring back inactive premium customers",
      "channel": "WhatsApp",
      "tone": "Friendly"
    }
    """
    data = request.json or {}
    goal = data.get('goal', '').strip()
    channel = data.get('channel', 'WhatsApp')
    tone = data.get('tone', 'Friendly')
    
    if not goal:
        return jsonify({'error': 'Goal is required'}), 400
        
    content = GeminiService.generate_campaign_content(goal, channel, tone)
    return jsonify(content)

@ai_agent_bp.route('/api/dashboard/recommendations', methods=['GET'])
def get_recommendations():
    """
    Scans database and returns active AI Growth Recommendations.
    """
    # Trigger recommendations refresh dynamically
    recs = RecommendationEngine.generate_recommendations()
    return jsonify(recs)

@ai_agent_bp.route('/api/recommendation/apply', methods=['POST'])
def apply_recommendation():
    """
    Marks a recommendation as applied.
    Body: { "recommendation_id": 1 }
    """
    data = request.json or {}
    rec_id = data.get('recommendation_id')
    
    rec = AIRecommendation.query.get(rec_id)
    if not rec:
        return jsonify({'error': 'Recommendation not found'}), 404
        
    rec.status = 'Applied'
    db.session.commit()
    return jsonify({'status': 'Applied', 'recommendation_id': rec_id})
