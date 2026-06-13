import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask App
app = Flask(__name__)

# Configure CORS
# In production, specify the actual frontend URL (e.g. from Vercel)
CORS(app, origins=[
    "https://xeno-growthpilot-ai-frontend.vercel.app"
])

# Configure Database
# Default to local SQLite for instant zero-config setup, but easily overridden with MySQL URL
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///growthpilot.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import db and trigger initialization
from database.db import db, seed_database
db.init_app(app)

# Import blueprints
from routes.customers import customers_bp
from routes.campaigns import campaigns_bp
from routes.ai_agent import ai_agent_bp
from routes.analytics import analytics_bp

# Register blueprints
app.register_blueprint(customers_bp)
app.register_blueprint(campaigns_bp)
app.register_blueprint(ai_agent_bp)
app.register_blueprint(analytics_bp)

# Healthcheck Route
@app.route("/api/health", methods=["GET"])
def healthcheck():
    return jsonify({
        "status": "healthy",
        "service": "GrowthPilot CRM Backend",
        "database": DATABASE_URL.split(":")[0]
    })

# Initialize and seed database inside app context
with app.app_context():
    db.create_all()
    seed_database(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting CRM Backend on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
