from flask import Blueprint, request, jsonify
from database.db import db
from models.customer import Customer
from models.order import Order
from datetime import datetime
import csv
import io
import re

customers_bp = Blueprint('customers', __name__)

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@customers_bp.route('/api/customers', methods=['GET'])
def get_customers():
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    
    # Query parameters
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    city = request.args.get('city', '', type=str)
    gender = request.args.get('gender', '', type=str)
    
    sort_by = request.args.get('sort_by', 'id', type=str)
    sort_order = request.args.get('sort_order', 'asc', type=str)

    query = Customer.query
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Customer.name.ilike(search_pattern) | 
            Customer.email.ilike(search_pattern) | 
            Customer.phone.ilike(search_pattern) |
            Customer.city.ilike(search_pattern)
        )
        
    # Apply filters
    if status:
        query = query.filter(Customer.status == status)
    if city:
        query = query.filter(Customer.city.ilike(city))
    if gender:
        query = query.filter(Customer.gender == gender)
        
    # Apply sorting
    if hasattr(Customer, sort_by):
        column = getattr(Customer, sort_by)
        if sort_order.lower() == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
            
    # Execute paginated query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'customers': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })

@customers_bp.route('/api/customers/upload', methods=['POST'])
def upload_customers():
    """
    Imports customer data from a CSV file.
    Expects CSV headers: name, email, phone, city, gender, age, lifetime_spend, total_orders, last_purchase_date, clv, risk_score, status
    """
    csv_file = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            csv_file = io.StringIO(file.read().decode('utf-8'))
    elif request.data:
        # Support raw text upload
        csv_file = io.StringIO(request.data.decode('utf-8'))
        
    if not csv_file:
        return jsonify({'error': 'No file uploaded'}), 400

    reader = csv.DictReader(csv_file)
    
    success_count = 0
    failed_records = []
    
    # Process rows
    for index, row in enumerate(reader):
        row_num = index + 2  # 1-based, accounts for header
        
        # Validations
        name = row.get('name', '').strip()
        email = row.get('email', '').strip()
        phone = row.get('phone', '').strip()
        city = row.get('city', '').strip()
        gender = row.get('gender', '').strip()
        age_str = row.get('age', '').strip()
        spend_str = row.get('lifetime_spend', '0').strip()
        orders_str = row.get('total_orders', '0').strip()
        last_pur_str = row.get('last_purchase_date', '').strip()
        clv_str = row.get('clv', '0').strip()
        risk_str = row.get('risk_score', '0').strip()
        status = row.get('status', 'Active').strip()

        errors = []
        if not name:
            errors.append("Name is required")
        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append(f"Invalid email address: {email}")
        
        # Parse numeric values with try/except
        try:
            age = int(age_str) if age_str else None
            if age is not None and (age < 0 or age > 120):
                errors.append("Age must be between 0 and 120")
        except ValueError:
            errors.append(f"Invalid age value: {age_str}")
            age = None

        try:
            spend = float(spend_str) if spend_str else 0.0
            if spend < 0:
                errors.append("Lifetime spend cannot be negative")
        except ValueError:
            errors.append(f"Invalid spend value: {spend_str}")
            spend = 0.0

        try:
            orders = int(orders_str) if orders_str else 0
            if orders < 0:
                errors.append("Total orders cannot be negative")
        except ValueError:
            errors.append(f"Invalid total orders value: {orders_str}")
            orders = 0

        try:
            clv = float(clv_str) if clv_str else 0.0
        except ValueError:
            clv = 0.0

        try:
            risk = float(risk_str) if risk_str else 0.0
            if risk < 0.0 or risk > 1.0:
                errors.append("Risk score must be between 0.0 and 1.0")
        except ValueError:
            errors.append(f"Invalid risk score: {risk_str}")
            risk = 0.0

        # Parse date
        last_purchase_date = None
        if last_pur_str:
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%m/%d/%Y'):
                try:
                    last_purchase_date = datetime.strptime(last_pur_str, fmt)
                    break
                except ValueError:
                    continue
            if not last_purchase_date:
                errors.append(f"Invalid date format: {last_pur_str}. Expected YYYY-MM-DD")

        # Check for duplicate email in this upload
        existing = Customer.query.filter_by(email=email).first()
        
        if errors:
            failed_records.append({
                'row': row_num,
                'name': name or 'Unknown',
                'email': email or 'Unknown',
                'reasons': errors
            })
            continue

        if existing:
            # Update customer details
            existing.name = name
            existing.phone = phone
            existing.city = city
            existing.gender = gender
            existing.age = age
            existing.lifetime_spend = spend
            existing.total_orders = orders
            existing.last_purchase_date = last_purchase_date
            existing.clv = clv
            existing.risk_score = risk
            existing.status = status
        else:
            # Create new customer
            new_cust = Customer(
                name=name,
                email=email,
                phone=phone,
                city=city,
                gender=gender,
                age=age,
                lifetime_spend=spend,
                total_orders=orders,
                last_purchase_date=last_purchase_date,
                clv=clv,
                risk_score=risk,
                status=status
            )
            db.session.add(new_cust)

        success_count += 1
        
    db.session.commit()
    
    return jsonify({
        'status': 'success' if len(failed_records) == 0 else 'partial_success',
        'total_records_processed': success_count + len(failed_records),
        'total_imported': success_count,
        'failed_records_count': len(failed_records),
        'failed_records': failed_records[:20],  # Return first 20 errors
        'validation_status': 'Verified' if len(failed_records) == 0 else 'Errors Encountered'
    })

@customers_bp.route('/api/orders/upload', methods=['POST'])
def upload_orders():
    """
    Imports order data from a CSV file.
    Headers: customer_email, amount, status, order_date
    """
    csv_file = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            csv_file = io.StringIO(file.read().decode('utf-8'))
    elif request.data:
        csv_file = io.StringIO(request.data.decode('utf-8'))
        
    if not csv_file:
        return jsonify({'error': 'No file uploaded'}), 400

    reader = csv.DictReader(csv_file)
    success_count = 0
    failed_records = []
    
    for index, row in enumerate(reader):
        row_num = index + 2
        email = row.get('customer_email', '').strip()
        amount_str = row.get('amount', '').strip()
        status = row.get('status', 'Completed').strip()
        order_date_str = row.get('order_date', '').strip()
        
        errors = []
        if not email:
            errors.append("customer_email is required")
            
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append("Amount must be greater than 0")
        except ValueError:
            errors.append(f"Invalid amount: {amount_str}")
            amount = 0.0
            
        order_date = None
        if order_date_str:
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%m/%d/%Y'):
                try:
                    order_date = datetime.strptime(order_date_str, fmt)
                    break
                except ValueError:
                    continue
        if not order_date:
            order_date = datetime.utcnow()
            
        # Match customer by email
        customer = Customer.query.filter_by(email=email).first()
        if not customer:
            errors.append(f"Customer email not found: {email}")
            
        if errors:
            failed_records.append({
                'row': row_num,
                'email': email or 'Unknown',
                'reasons': errors
            })
            continue
            
        # Create order
        new_order = Order(
            customer_id=customer.id,
            order_date=order_date,
            amount=amount,
            status=status
        )
        db.session.add(new_order)
        
        # Update customer stats
        if status == 'Completed':
            customer.total_orders += 1
            customer.lifetime_spend += amount
            # Update last purchase date if newer
            if not customer.last_purchase_date or order_date > customer.last_purchase_date:
                customer.last_purchase_date = order_date
            customer.clv = round(customer.lifetime_spend * 1.5, 2)
            
        success_count += 1
        
    db.session.commit()
    
    return jsonify({
        'status': 'success' if len(failed_records) == 0 else 'partial_success',
        'total_records_processed': success_count + len(failed_records),
        'total_imported': success_count,
        'failed_records_count': len(failed_records),
        'failed_records': failed_records[:20]
    })
