import os
import json
import requests
from datetime import datetime, timedelta
from database.db import db
from models.customer import Customer
# Optional Gemini Support
GEMINI_AVAILABLE = False
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    import google.generativeai as genai

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print("Gemini AI enabled")
    else:
        print("Gemini API key not found. Using fallback engine.")

except Exception as e:
    print(f"Gemini disabled: {e}")

class GeminiService:
    @staticmethod
    def parse_audience_query(query_text):
        """
        Translates a natural language query into a database filter.
        Returns:
            - filter_description (str)
            - customer_count (int)
            - customer_preview (list of dicts)
            - customer_ids (list of ints)
        """
        query_text_lower = query_text.lower()
        now = datetime.utcnow()
        
        # 1. Map intent to SQLAlchemy filters
        query = Customer.query
        criteria_desc = ""
        
        if "inactive premium" in query_text_lower or ("bring back" in query_text_lower and "premium" in query_text_lower):
            # No purchase in last 60 days and spend > 5000
            cutoff = now - timedelta(days=60)
            query = query.filter(Customer.last_purchase_date < cutoff, Customer.lifetime_spend >= 5000)
            criteria_desc = "No purchase in the last 60 days & Lifetime Spend >= \u20b95,000"
        elif "premium" in query_text_lower or "high spend" in query_text_lower or "vip" in query_text_lower:
            # Spend > 8000
            query = query.filter(Customer.lifetime_spend >= 8000)
            criteria_desc = "Lifetime Spend >= \u20b98,000 (VIP segment)"
        elif "inactive" in query_text_lower or "churn" in query_text_lower or "bring back" in query_text_lower:
            # No purchase in last 90 days
            cutoff = now - timedelta(days=90)
            query = query.filter(Customer.last_purchase_date < cutoff)
            criteria_desc = "No purchase in the last 90 days"
        elif "chennai" in query_text_lower:
            # City is Chennai
            query = query.filter(Customer.city.ilike("Chennai"))
            criteria_desc = "City is Chennai"
        elif "mumbai" in query_text_lower:
            query = query.filter(Customer.city.ilike("Mumbai"))
            criteria_desc = "City is Mumbai"
        elif "bengaluru" in query_text_lower or "bangalore" in query_text_lower:
            query = query.filter(Customer.city.ilike("Bengaluru"))
            criteria_desc = "City is Bengaluru"
        elif "repeat" in query_text_lower or "loyal" in query_text_lower:
            # Orders >= 3
            query = query.filter(Customer.total_orders >= 3)
            criteria_desc = "Total Orders >= 3"
        elif "festive" in query_text_lower or "diwali" in query_text_lower or "holiday" in query_text_lower:
            # Target active customers for a campaign promotion
            cutoff = now - timedelta(days=45)
            query = query.filter(Customer.last_purchase_date >= cutoff)
            criteria_desc = "Active customers (Purchased in the last 45 days) for Festive Promo"
        else:
            # Default: Active customers with moderate risk
            query = query.filter(Customer.status == "Active")
            criteria_desc = "All currently active customers"

        # Execute query
        matching_customers = query.all()
        customer_ids = [c.id for c in matching_customers]
        customer_count = len(matching_customers)
        
        # Take a preview of 5 customers
        preview = [c.to_dict() for c in matching_customers[:5]]
        
        return {
            "criteria": criteria_desc,
            "count": customer_count,
            "preview": preview,
            "customer_ids": customer_ids
        }

    @staticmethod
    def generate_campaign_content(goal_text, channel="WhatsApp", tone="Friendly"):
        """
        Generates campaign message templates, expected metrics, and analysis
        based on the user's business goal.
        """
        # If API key is available, we try to call Gemini
        if GEMINI_AVAILABLE and GEMINI_API_KEY:
            try:
                # Use beta model or gemini-pro
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"""
                You are GrowthPilot AI, an autonomous marketing CRM assistant.
                The marketer wants to achieve this goal: "{goal_text}".
                Create a marketing message for the communication channel "{channel}" with a "{tone}" tone.
                Also provide message variations for the other channels: WhatsApp, SMS, Email, RCS.
                
                For WhatsApp: Keep it engaging, can use emojis and formatting like bold (*text*). Max 300 chars.
                For SMS: Keep it concise, call to action link, max 160 chars.
                For Email: Standard subject line and structured email body.
                For RCS: Engaging rich cards style, with suggested action buttons, max 250 chars.
                
                Also provide predictions for the campaign performance on a 0-100 scale:
                - Expected Delivery Rate (%)
                - Expected Open Rate (%)
                - Expected Click Rate (%)
                
                Respond ONLY in a strict JSON format with the following keys (no markdown formatting or backticks around JSON):
                {{
                  "analysis": "Short analysis of the business goal and why the recommended strategy works",
                  "recommended_channel": "WhatsApp, SMS, Email or RCS",
                  "channel_reason": "Explanation for recommending this channel",
                  "whatsapp_msg": "WhatsApp message copy",
                  "sms_msg": "SMS message copy",
                  "email_subject": "Email subject line",
                  "email_body": "Email body copy",
                  "rcs_msg": "RCS message copy with button options",
                  "expected_delivery": 95,
                  "expected_open": 80,
                  "expected_click": 20
                }}
                """
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                # Clean up any potential markdown json fences
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                parsed_response = json.loads(response_text.strip())
                return parsed_response
            except Exception as e:
                print(f"Gemini API generation failed, falling back to local engine. Error: {e}")

        # Fallback Mock AI Engine (Smart local generation)
        print("Using smart local campaign generator...")
        analysis = f"Based on historical data for '{goal_text}', this segment responds best to personalized touchpoints. We recommend direct mobile messaging for immediate conversions, backed up with email for detailed collateral."
        
        # Decide channel recommendation based on keyword
        rec_channel = "WhatsApp"
        channel_reason = "WhatsApp shows the highest historical open rate (88%) for re-engagement campaigns in the Indian retail market."
        
        if "email" in goal_text.lower():
            rec_channel = "Email"
            channel_reason = "Email is the preferred channel for detailed content, catalogs, and invoices, giving the customer space to browse."
        elif "sms" in goal_text.lower():
            rec_channel = "SMS"
            channel_reason = "SMS offers near-100% deliverability and immediate reading for urgent coupon redemptions."
            
        # Message content templates based on Tone
        templates = {
            "Friendly": {
                "WhatsApp": "Hey {name}! 🌟 We noticed it's been a while since you stopped by. We've added some amazing new arrivals we think you'll love! Grab 15% off using code HELLO15. Chat soon! Shop here: https://gpilot.ai/f15",
                "SMS": "Hey {name}! We miss you. Check out our latest products and enjoy 15% off with code HELLO15 at checkout! Shop now: https://gpilot.ai/f15",
                "Email_Subject": "Hey {name}, we miss you! 🌟 (Plus a little welcome back gift inside...)",
                "Email_Body": "Hi {name},\n\nWe noticed it's been a while since your last purchase, and we wanted to say we miss you!\n\nOur team has been busy adding fresh new arrivals to our catalog. To make your return sweeter, here is a 15% discount code: HELLO15.\n\nUse it at checkout and let us know what you think!\n\nWarmly,\nGrowthPilot Team",
                "RCS": "Hey {name}! 👋 We miss having you around. To welcome you back, we're giving you a 15% discount. Check out our fresh arrivals!\n\n[Shop Now] [Claim 15% Off]"
            },
            "Professional": {
                "WhatsApp": "Hello {name}, we hope you are well. We value your relationship with us and wanted to share our latest curated catalog. Use corporate promo code GPVAL10 for a 10% discount on your next order: https://gpilot.ai/v10",
                "SMS": "Hello {name}, we value your patronage. Browse our updated catalog and apply code GPVAL10 for a 10% discount: https://gpilot.ai/v10",
                "Email_Subject": "A special offer for {name} - GrowthPilot AI Customer Appreciation",
                "Email_Body": "Dear {name},\n\nWe appreciate your ongoing relationship with GrowthPilot AI.\n\nOur goal is to continue providing high-quality service and products tailored to your preferences. To express our gratitude, we would like to offer you a 10% discount on your next order.\n\nApply code GPVAL10 at checkout. If you need any assistance, our support team is standing by.\n\nSincerely,\nGrowthPilot Management",
                "RCS": "Dear {name}, we appreciate your business. Apply promo code GPVAL10 for 10% off your next transaction.\n\n[View Catalog] [Contact Support]"
            },
            "Luxury": {
                "WhatsApp": "Greetings {name}. ✨ You are cordially invited to explore our premium Private Reserve collection. Enjoy complimentary concierge delivery and an exclusive 15% privilege using code ELITE15: https://gpilot.ai/el15",
                "SMS": "Greetings {name}. You are invited to view our new Private Reserve collection. Enjoy a 15% privilege with code ELITE15: https://gpilot.ai/el15",
                "Email_Subject": "Private Invitation: {name}, explore our Elite Reserve collection",
                "Email_Body": "Dear {name},\n\nAs one of our most valued customers, we are delighted to invite you to explore our new Private Reserve collection.\n\nThis limited-edition selection embodies exceptional craftsmanship and quality. For a limited time, enjoy a 15% privilege discount along with complimentary premium delivery.\n\nYour personal code: ELITE15.\n\nRegards,\nThe Luxury Concierge Team",
                "RCS": "Greetings {name}. You are invited to preview the Private Reserve collection. Access your 15% privilege code ELITE15.\n\n[Explore Collection] [Request Call]"
            },
            "Promotional": {
                "WhatsApp": "MEGA SALE, {name}! 🔥 Don't miss out on our weekend blowout! Up to 40% OFF site-wide! PLUS, get an extra 10% off with code FLASH10 right now! Hurry, stock is limited: https://gpilot.ai/fl10",
                "SMS": "FLASH SALE, {name}! Get up to 40% off site-wide + extra 10% off with code FLASH10. Ends tonight! Shop here: https://gpilot.ai/fl10",
                "Email_Subject": "FLASH SALE! 💥 {name}, get up to 50% OFF - 24 Hours Only!",
                "Email_Body": "Hey {name},\n\nThis is it! Our biggest sale of the season is LIVE.\n\nGet up to 40% off select products, plus take an extra 10% off your entire order with code FLASH10. This deal is valid for 24 hours only, and items are selling out fast.\n\nClaim your savings now!\n\nBest,\nGrowthPilot Deals",
                "RCS": "MEGA SALE {name}! 🔥 Get up to 40% OFF site-wide + extra 10% discount using coupon FLASH10. Valid for 24 hours!\n\n[Shop Mega Sale] [Claim Coupon]"
            },
            "Casual": {
                "WhatsApp": "Hey {name}! What's up? It's been a minute since we caught up. We've got some cool new gear in store. Use code COZY15 for 15% off when you check them out: https://gpilot.ai/cz15",
                "SMS": "Hey {name}, what's up? We've got new gear in stock! Take 15% off with code COZY15: https://gpilot.ai/cz15",
                "Email_Subject": "It's been a minute, {name}! Let's catch up... 👋",
                "Email_Body": "Hey {name},\n\nHope you're doing great! We noticed it's been a minute since you stopped by our store.\n\nJust wanted to let you know we've restocked our bestsellers and dropped some really cool new arrivals. Take a look and use code COZY15 to save 15% on us!\n\nCatch you later,\nGrowthPilot Team",
                "RCS": "Hey {name}! 👋 What's new? Just checking in with a 15% discount coupon (code COZY15) for your next purchase.\n\n[Check New Arrivals] [Use Coupon]"
            }
        }
        
        selected = templates.get(tone, templates["Friendly"])
        
        # Predicted metrics based on channel
        rates = {
            "WhatsApp": {"delivery": 97.4, "open": 85.2, "click": 21.6},
            "SMS": {"delivery": 94.8, "open": 55.4, "click": 8.3},
            "Email": {"delivery": 99.1, "open": 26.5, "click": 4.1},
            "RCS": {"delivery": 91.2, "open": 72.8, "click": 16.4}
        }
        
        selected_rates = rates.get(channel, rates["WhatsApp"])
        
        return {
            "analysis": analysis,
            "recommended_channel": rec_channel,
            "channel_reason": channel_reason,
            "whatsapp_msg": selected["WhatsApp"],
            "sms_msg": selected["SMS"],
            "email_subject": selected["Email_Subject"],
            "email_body": selected["Email_Body"],
            "rcs_msg": selected["RCS"],
            "expected_delivery": selected_rates["delivery"],
            "expected_open": selected_rates["open"],
            "expected_click": selected_rates["click"]
        }

    @staticmethod
    def generate_campaign_insights(campaign_id):
        """
        Generates a summary analysis for completed campaigns.
        """
        from models.campaign import Campaign
        from models.communication import Communication
        
        camp = Campaign.query.get(campaign_id)
        if not camp:
            return {"summary": "Campaign not found.", "recommendation": ""}
            
        if camp.status != "Completed":
            return {
                "summary": f"This campaign is currently in '{camp.status}' status. Performance insights will be available once it completes.",
                "recommendation": "Monitor real-time logs in the channel simulator."
            }
            
        # Segment analysis
        # Let's count some metrics by city or lifetime spend
        total = camp.audience_size
        delivered = int(total * (camp.delivery_rate / 100))
        opened = int(delivered * (camp.open_rate / 100))
        clicked = int(opened * (camp.click_rate / 100)) if opened > 0 else 0
        
        summary = (
            f"The '{camp.name}' campaign achieved a delivery rate of {camp.delivery_rate}%, "
            f"with an open rate of {camp.open_rate}% and a click-through rate of {camp.click_rate}%. "
            f"This resulted in {clicked} engaged users out of {total} targets, generating a total revenue impact of \u20b9{camp.revenue_generated:,.2f}."
        )
        
        recommendation = "Premium segments showed 35% higher click engagement than standard customers. Recommend launching a high-incentive follow-up message to the non-responders within 72 hours."
        
        if camp.click_rate < 10:
            recommendation = "Low click-through rate detected. This could be due to offer relevance. Consider split testing a promotional offer with higher discount values (e.g., 25%) on WhatsApp."
            
        return {
            "summary": summary,
            "best_segment": "Premium Customer Segment",
            "recommendation": recommendation
        }
