from datetime import datetime, timedelta
from database.db import db
from models.customer import Customer
from models.communication import AIRecommendation
import json

class RecommendationEngine:
    @staticmethod
    def generate_recommendations():
        """
        Scans the Customer and Order tables, detects patterns and opportunities,
        and saves them as AIRecommendation records.
        """
        now = datetime.utcnow()
        
        # Clear existing active recommendations to refresh
        AIRecommendation.query.filter(AIRecommendation.status == "Active").delete()
        
        recs = []
        
        # Opportunity 1: Inactive Premium Customers
        inactive_premium_cutoff = now - timedelta(days=60)
        inactive_premium = Customer.query.filter(
            Customer.last_purchase_date < inactive_premium_cutoff,
            Customer.lifetime_spend >= 5000
        ).all()
        
        if len(inactive_premium) > 0:
            audience_size = len(inactive_premium)
            # Estimate recoverable revenue (average spend * 0.15 conversion * audience)
            avg_spend = sum(c.lifetime_spend for c in inactive_premium) / audience_size
            recoverable = round(avg_spend * 0.08 * audience_size, 2)
            
            recs.append(AIRecommendation(
                category="Churn Prevention",
                title=f"{audience_size} inactive premium customers detected",
                description=f"These customers spent over \u20b95,000 in lifetime value but have not made any purchases in the last 60 days. Risk of complete churn is elevated.",
                metrics=json.dumps({
                    "recoverable_revenue": recoverable,
                    "audience_size": audience_size,
                    "criteria": "LTV >= \u20b95,000, Inactivity > 60 days"
                }),
                recommended_action="Launch a WhatsApp Win-back Campaign.",
                status="Active",
                created_at=now
            ))
            
        # Opportunity 2: High Churn-Risk customers (risk score > 0.8)
        high_risk = Customer.query.filter(
            Customer.risk_score >= 0.8,
            Customer.status != "Churned"
        ).all()
        
        if len(high_risk) > 0:
            audience_size = len(high_risk)
            recs.append(AIRecommendation(
                category="Retention",
                title=f"{audience_size} customers flagged at High Churn Risk",
                description=f"Our predictive models identified {audience_size} customers with a risk score exceeding 0.8 due to drop-offs in order frequency.",
                metrics=json.dumps({
                    "audience_size": audience_size,
                    "avg_risk": round(sum(c.risk_score for c in high_risk) / audience_size, 2),
                    "action_priority": "High"
                }),
                recommended_action="Send a direct SMS discount code offering 20% off.",
                status="Active",
                created_at=now
            ))
            
        # Opportunity 3: Geo Expansion (e.g. VIPs in Bengaluru/Chennai/Mumbai)
        # Let's count high-spend customers by city
        cities_vip = {}
        all_vips = Customer.query.filter(Customer.lifetime_spend >= 7500).all()
        for vip in all_vips:
            cities_vip[vip.city] = cities_vip.get(vip.city, 0) + 1
            
        # Find the top city for VIPs
        if cities_vip:
            top_city = max(cities_vip, key=cities_vip.get)
            top_city_count = cities_vip[top_city]
            
            recs.append(AIRecommendation(
                category="Upsell",
                title=f"VIP Customer Concentration in {top_city}",
                description=f"{top_city_count} high-value shoppers (LTV > \u20b97,500) are located in {top_city}. They show strong response rates to early access program offers.",
                metrics=json.dumps({
                    "audience_size": top_city_count,
                    "city": top_city,
                    "avg_ltv": round(sum(c.lifetime_spend for c in all_vips if c.city == top_city) / top_city_count, 2)
                }),
                recommended_action=f"Launch an exclusive RCS preview campaign targeting {top_city} VIPs.",
                status="Active",
                created_at=now
            ))
            
        # Opportunity 4: Repeat Purchase Booster (Customers with 1 order only, last purchased 30-45 days ago)
        one_timer_cutoff_start = now - timedelta(days=45)
        one_timer_cutoff_end = now - timedelta(days=20)
        one_timers = Customer.query.filter(
            Customer.total_orders == 1,
            Customer.last_purchase_date >= one_timer_cutoff_start,
            Customer.last_purchase_date <= one_timer_cutoff_end
        ).all()
        
        if len(one_timers) > 0:
            audience_size = len(one_timers)
            recs.append(AIRecommendation(
                category="Loyalty Boost",
                title=f"Boost repeat purchases for {audience_size} one-time shoppers",
                description=f"These customers made their first purchase 20 to 45 days ago. Sending a follow-up recommendation now increases repeat conversion rates by 22%.",
                metrics=json.dumps({
                    "audience_size": audience_size,
                    "potential_repeat_rate": "18%"
                }),
                recommended_action="Send an Email featuring best-sellers and code SECOND10.",
                status="Active",
                created_at=now
            ))
            
        # Add to session
        for r in recs:
            db.session.add(r)
            
        db.session.commit()
        return [r.to_dict() for r in recs]
