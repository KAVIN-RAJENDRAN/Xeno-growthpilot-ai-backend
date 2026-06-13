import random
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Lists of realistic Indian names and data for seeding
FIRST_NAMES_MALE = [
    "Aarav", "Aditya", "Amit", "Arjun", "Deepak", "Dev", "Hari", "Ishaan", 
    "Karan", "Madhav", "Nikhil", "Pranav", "Rahul", "Rajesh", "Rohan", "Sanjay", 
    "Suresh", "Vikram", "Vijay", "Yash", "Abhishek", "Vivek", "Anil", "Sunil"
]

FIRST_NAMES_FEMALE = [
    "Aanya", "Ananya", "Deepa", "Divya", "Kavita", "Meera", "Neha", "Pooja", 
    "Priya", "Rhea", "Ritu", "Sneha", "Sunita", "Tanvi", "Vanisha", "Shruti", 
    "Anjali", "Swati", "Aarti", "Geeta", "Kajal", "Shalini", "Payal", "Preeti"
]

LAST_NAMES = [
    "Kumar", "Sharma", "Patel", "Nair", "Iyer", "Singh", "Rao", "Gupta", 
    "Verma", "Reddy", "Joshi", "Saxena", "Mehta", "Chawla", "Deshmukh", "Pillai",
    "Sen", "Banerjee", "Chatterjee", "Dutta", "Das", "Menon", "Shenoy", "Bhat"
]

CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"]

CAMPAIGN_GOALS = [
    "Bring back inactive premium customers",
    "Promote festive Diwali sale",
    "Cross-sell premium accessories to recent buyers",
    "Encourage repeat purchases with coupon codes",
    "Re-engage churn-risk users",
    "Target high-value Chennai shoppers",
    "Upsell loyalty program subscriptions",
    "Announce new weekend flash sale",
    "Collect feedback from inactive users",
    "Launch new eco-friendly collection"
]

CAMPAIGN_NAMES = [
    "WhatsApp Win-Back Campaign",
    "Diwali Festive Special",
    "Premium Cross-sell Push",
    "Repeat Purchase Booster",
    "Re-engagement SMS Campaign",
    "Chennai VIP Flash Sale",
    "GrowthPilot Loyalty Promo",
    "Weekend Rush Discount",
    "Inactive User Survey",
    "Eco-Friendly Launch"
]

def seed_database(app):
    """
    Seeds the database with 1000+ customers, 5000+ orders, 50+ campaigns, 
    and detailed communication logs.
    """
    from models.customer import Customer
    from models.order import Order
    from models.campaign import Campaign
    from models.communication import Communication, CommunicationEvent, Segment, AIRecommendation

    with app.app_context():
        # Check if database is already seeded
        if Customer.query.first() is not None:
            print("Database already seeded.")
            return

        print("Seeding database... This might take a moment.")
        
        # 1. Generate Customers (1000+)
        customers = []
        now = datetime.utcnow()
        
        for i in range(1050):
            gender = random.choice(["Male", "Female"])
            first_name = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
            last_name = random.choice(LAST_NAMES)
            name = f"{first_name} {last_name}"
            
            email = f"{first_name.lower()}.{last_name.lower()}.{random.randint(10,999)}@gmail.com"
            phone = f"+91 {random.choice([98, 97, 96, 95, 88, 77])}{random.randint(10000000, 99999999)}"
            city = random.choice(CITIES)
            age = random.randint(18, 65)
            
            # Spend distributions: some VIPs, many average, some low
            cohort = random.choices(["VIP", "Average", "Low"], weights=[0.15, 0.65, 0.20])[0]
            if cohort == "VIP":
                total_orders = random.randint(8, 25)
                lifetime_spend = round(random.uniform(8000, 45000), 2)
            elif cohort == "Average":
                total_orders = random.randint(2, 7)
                lifetime_spend = round(random.uniform(1000, 7999), 2)
            else:
                total_orders = 1
                lifetime_spend = round(random.uniform(150, 999), 2)
            
            clv = round(lifetime_spend * random.uniform(1.1, 1.8), 2)
            
            # Last purchase date
            last_purchase_days_ago = random.randint(1, 150)
            last_purchase_date = now - timedelta(days=last_purchase_days_ago)
            
            # Risk Score and Status logic
            if last_purchase_days_ago > 90:
                risk_score = round(random.uniform(0.7, 0.99), 2)
                status = "Churned"
            elif last_purchase_days_ago > 45:
                risk_score = round(random.uniform(0.4, 0.75), 2)
                status = "At Risk"
            else:
                risk_score = round(random.uniform(0.05, 0.39), 2)
                status = "Active"
                
            cust = Customer(
                name=name,
                email=email,
                phone=phone,
                city=city,
                gender=gender,
                age=age,
                lifetime_spend=lifetime_spend,
                total_orders=total_orders,
                last_purchase_date=last_purchase_date,
                clv=clv,
                risk_score=risk_score,
                status=status
            )
            db.session.add(cust)
            customers.append(cust)
        
        # Commit customers so we get IDs
        db.session.commit()
        print(f"Imported {len(customers)} customers.")
        
        # 2. Generate Orders (5000+ orders)
        orders_count = 0
        for cust in customers:
            # Generate total_orders for each customer
            rem_spend = cust.lifetime_spend
            num_orders = cust.total_orders
            
            # Break down total spend into orders
            amounts = []
            if num_orders == 1:
                amounts = [rem_spend]
            else:
                # Distribute random amounts
                for j in range(num_orders - 1):
                    amt = round(random.uniform(0.05 * rem_spend, 0.4 * rem_spend), 2)
                    amounts.append(amt)
                    rem_spend -= amt
                amounts.append(round(rem_spend, 2))
                
            # Create Order records
            for k in range(num_orders):
                order_days_ago = random.randint(cust.last_purchase_date.day if (now - cust.last_purchase_date).days < 30 else 30, 365)
                # Ensure last purchase date has the actual last purchase date
                if k == num_orders - 1:
                    order_date = cust.last_purchase_date
                else:
                    order_date = now - timedelta(days=order_days_ago)
                    
                order = Order(
                    customer_id=cust.id,
                    order_date=order_date,
                    amount=amounts[k],
                    status=random.choices(["Completed", "Cancelled", "Refunded"], weights=[0.94, 0.04, 0.02])[0]
                )
                db.session.add(order)
                orders_count += 1
                
            if orders_count % 1000 == 0:
                db.session.flush()
                
        db.session.commit()
        print(f"Imported {orders_count} orders.")

        # 3. Generate Campaigns (50)
        campaigns = []
        channels = ["WhatsApp", "SMS", "Email", "RCS"]
        statuses = ["Completed", "Running", "Scheduled", "Draft", "Failed"]
        
        # Seed 50 campaigns
        for i in range(50):
            # Create varied campaign history
            created_days_ago = random.randint(5, 120)
            created_date = now - timedelta(days=created_days_ago)
            
            if i < 40:
                status = "Completed"
            elif i < 44:
                status = "Running"
            elif i < 47:
                status = "Scheduled"
            elif i < 49:
                status = "Draft"
            else:
                status = "Failed"
                
            channel = random.choice(channels)
            goal = random.choice(CAMPAIGN_GOALS)
            name = f"{channel} - {random.choice(CAMPAIGN_NAMES)} #{i+100}"
            
            audience_size = random.randint(50, 400)
            
            # Realistic engagement rates based on channel
            if status == "Completed":
                if channel == "WhatsApp":
                    del_rate = round(random.uniform(94, 99), 1)
                    op_rate = round(random.uniform(75, 92), 1)
                    cl_rate = round(random.uniform(18, 30), 1)
                elif channel == "RCS":
                    del_rate = round(random.uniform(90, 96), 1)
                    op_rate = round(random.uniform(60, 80), 1)
                    cl_rate = round(random.uniform(12, 22), 1)
                elif channel == "SMS":
                    del_rate = round(random.uniform(92, 98), 1)
                    op_rate = round(random.uniform(40, 60), 1)
                    cl_rate = round(random.uniform(5, 12), 1)
                else:  # Email
                    del_rate = round(random.uniform(96, 99.8), 1)
                    op_rate = round(random.uniform(18, 35), 1)
                    cl_rate = round(random.uniform(2, 6), 1)
                
                rev_gen = round(audience_size * cl_rate * 0.05 * random.uniform(500, 2000), 2)
            elif status == "Running":
                del_rate = round(random.uniform(40, 80), 1)
                op_rate = round(random.uniform(20, 50), 1)
                cl_rate = round(random.uniform(5, 15), 1)
                rev_gen = round(audience_size * cl_rate * 0.02 * random.uniform(500, 1500), 2)
            else:
                del_rate = 0.0
                op_rate = 0.0
                cl_rate = 0.0
                rev_gen = 0.0
                
            msg_templates = {
                "WhatsApp": "Hey {name}! 🌟 We missed you! Here is an exclusive offer just for you: Get 20% off your next purchase using code WINBACK20. Valid till Sunday! Shop now: https://gpilot.ai/wb20",
                "SMS": "Hi {name}, we miss you! Enjoy 20% off your next order. Use code WINBACK20 at checkout: https://gpilot.ai/wb20 - GrowthPilot AI",
                "Email": "Subject: We Miss You, {name}! Open for an Exclusive 20% Discount\n\nDear {name},\n\nIt has been a while since your last purchase. We would love to welcome you back with a special 20% discount on our entire collection.\n\nUse code: WINBACK20 at checkout.\n\nBest regards,\nGrowthPilot Team",
                "RCS": "Hello {name}! 👋 Ready to come back? Tap below to claim a 20% coupon on your next order! 🎟️ [Claim Coupon] [Browse Collection]"
            }
            
            camp = Campaign(
                name=name,
                goal=goal,
                audience_size=audience_size,
                channel=channel,
                created_date=created_date,
                status=status,
                delivery_rate=del_rate,
                open_rate=op_rate,
                click_rate=cl_rate,
                revenue_generated=rev_gen,
                message_template=msg_templates[channel]
            )
            db.session.add(camp)
            campaigns.append(camp)
            
        db.session.commit()
        print(f"Imported {len(campaigns)} campaigns.")

        # 4. Generate Communication Logs for Completed & Running Campaigns
        print("Generating communication logs...")
        comm_count = 0
        for camp in campaigns:
            if camp.status not in ["Completed", "Running"]:
                continue
                
            # Sample a subset of customers for this campaign
            sampled_customers = random.sample(customers, camp.audience_size)
            
            # Determine how many should be Opened, Clicked, Failed based on rates
            num_delivered = int(camp.audience_size * (camp.delivery_rate / 100))
            num_opened = int(num_delivered * (camp.open_rate / 100))
            num_clicked = int(num_opened * (camp.click_rate / 100)) if num_opened > 0 else 0
            
            for index, cust in enumerate(sampled_customers):
                # Status progression
                if index < num_clicked:
                    c_status = "Clicked"
                elif index < num_opened:
                    c_status = "Opened"
                elif index < num_delivered:
                    c_status = "Delivered"
                elif index < camp.audience_size - 1:
                    c_status = "Sent"
                else:
                    c_status = "Failed"
                    
                comm = Communication(
                    customer_id=cust.id,
                    campaign_id=camp.id,
                    channel=camp.channel,
                    status=c_status,
                    sent_at=camp.created_date + timedelta(minutes=random.randint(5, 60))
                )
                
                # Assign status timestamps
                if c_status != "Failed":
                    comm.delivered_at = comm.sent_at + timedelta(seconds=random.randint(1, 15))
                if c_status in ["Opened", "Clicked"]:
                    comm.opened_at = comm.delivered_at + timedelta(minutes=random.randint(2, 120))
                    comm.read_at = comm.opened_at + timedelta(seconds=random.randint(5, 30))
                if c_status == "Clicked":
                    comm.clicked_at = comm.opened_at + timedelta(minutes=random.randint(1, 45))
                if c_status == "Failed":
                    comm.error_message = random.choice(["Unreachable number", "Invalid email domain", "Inbox full", "Spam block"])
                    
                db.session.add(comm)
                
                # Add events
                events = [("Sent", comm.sent_at)]
                if comm.delivered_at:
                    events.append(("Delivered", comm.delivered_at))
                if comm.opened_at:
                    events.append(("Opened", comm.opened_at))
                if comm.clicked_at:
                    events.append(("Clicked", comm.clicked_at))
                if comm.error_message:
                    events.append(("Failed", comm.sent_at + timedelta(seconds=2)))
                    
                db.session.flush() # flush to get comm.id
                
                for ev_type, ev_time in events:
                    event = CommunicationEvent(
                        communication_id=comm.id,
                        event_type=ev_type,
                        timestamp=ev_time
                    )
                    db.session.add(event)
                    
                comm_count += 1
                if comm_count % 2000 == 0:
                    db.session.flush()
                    
        db.session.commit()
        print(f"Imported {comm_count} communication events.")

        # 5. Seed static AI Recommendations
        recs = [
            AIRecommendation(
                category="Churn Prevention",
                title="428 inactive premium customers detected",
                description="Estimated recoverable revenue: \u20b91,24,000. These customers have a lifetime spend above \u20b95,000 but haven't ordered in the last 60 days.",
                metrics='{"recoverable_revenue": 124000, "audience_size": 428}',
                recommended_action="Launch a WhatsApp Win-back Campaign.",
                status="Active",
                created_at=now - timedelta(hours=4)
            ),
            AIRecommendation(
                category="High-Value Engagement",
                title="182 VIP Customers in Bengaluru",
                description="Estimated segment growth: 18% month-over-month. VIP shoppers are looking for early access to the upcoming collection launch.",
                metrics='{"revenue_potential": 85000, "audience_size": 182}',
                recommended_action="Launch an exclusive Email preview campaign.",
                status="Active",
                created_at=now - timedelta(hours=12)
            ),
            AIRecommendation(
                category="Abandonment Recovery",
                title="96 high Churn-Risk customers",
                description="Risk score > 0.85 detected for 96 customers. These users spent heavily in the past but their engagement has dropped dramatically.",
                metrics='{"risk_reduction_rate": "35%", "audience_size": 96}',
                recommended_action="Send a direct SMS with a 25% discount.",
                status="Active",
                created_at=now - timedelta(days=1)
            )
        ]
        for r in recs:
            db.session.add(r)
            
        # 6. Seed a sample segment
        seg = Segment(
            name="Inactive Premium Customers",
            criteria="No purchase in last 60 days, Lifetime spend > \u20b95000",
            customer_count=428,
            created_at=now - timedelta(days=3)
        )
        db.session.add(seg)
        
        db.session.commit()
        print("Database seeding completed successfully!")
