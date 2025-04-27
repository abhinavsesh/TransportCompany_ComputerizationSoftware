from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
import bcrypt
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tccs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'  # Change in production
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Manager or Employee
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=True)

class Consignment(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    volume = db.Column(db.Float, nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_address = db.Column(db.String(200), nullable=False)
    receiver_name = db.Column(db.String(100), nullable=False)
    receiver_address = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    charge = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dispatched_at = db.Column(db.DateTime, nullable=True)
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=False)

class Truck(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Available')
    capacity = db.Column(db.Float, default=500.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=False)

class Branch(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    location = db.Column(db.String(100), nullable=False)

class ConsignmentTruck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consignment_id = db.Column(db.String(36), db.ForeignKey('consignment.id'))
    truck_id = db.Column(db.String(36), db.ForeignKey('truck.id'))

# Authentication Decorator
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user or (role and user.role != role):
                return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper Functions
def calculate_charge(volume, destination):
    base_rate = 10  # $10 per cubic meter
    distance_factor = 1.5 if destination != 'Capital' else 1.0
    return volume * base_rate * distance_factor

def check_truck_allocation(destination, branch_id):
    total_volume = db.session.query(func.sum(Consignment.volume)).filter(
        Consignment.destination == destination,
        Consignment.status == 'Pending',
        Consignment.branch_id == branch_id
    ).scalar() or 0
    if total_volume >= 500:
        truck = Truck.query.filter_by(branch_id=branch_id, status='Available').first()
        if truck:
            consignments = Consignment.query.filter_by(destination=destination, status='Pending', branch_id=branch_id).all()
            for consignment in consignments:
                consignment.status = 'Dispatched'
                consignment.dispatched_at = datetime.utcnow()
                db.session.add(ConsignmentTruck(consignment_id=consignment.id, truck_id=truck.id))
            truck.status = 'In-Transit'
            truck.last_updated = datetime.utcnow()
            db.session.commit()
            return truck, consignments
    return None, []

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(username=data['username']).first()
        if user and bcrypt.checkpw(data['password'].encode('utf-8'), user.password.encode('utf-8')):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'Manager':
        branches = Branch.query.all()
        return render_template('manager_dashboard.html', branches=branches)
    return render_template('employee_dashboard.html', branch_id=user.branch_id)

@app.route('/consignments', methods=['POST'])
@login_required()
def add_consignment():
    user = User.query.get(session['user_id'])
    data = request.json
    branch_id = user.branch_id if user.role == 'Employee' else data.get('branch_id')
    if not branch_id:
        return jsonify({'error': 'Branch ID required'}), 400
    charge = calculate_charge(data['volume'], data['destination'])
    consignment = Consignment(
        volume=data['volume'],
        destination=data['destination'],
        sender_name=data['sender_name'],
        sender_address=data['sender_address'],
        receiver_name=data['receiver_name'],
        receiver_address=data['receiver_address'],
        charge=charge,
        branch_id=branch_id
    )
    db.session.add(consignment)
    db.session.commit()
    truck, consignments = check_truck_allocation(data['destination'], branch_id)
    if truck:
        return jsonify({
            'message': 'Consignment added and truck allocated',
            'truck_id': truck.id,
            'consignments': [{'id': c.id, 'volume': c.volume} for c in consignments]
        }), 201
    return jsonify({'message': 'Consignment added'}), 201

@app.route('/consignments/<id>', methods=['GET'])
@login_required()
def get_consignment(id):
    consignment = Consignment.query.get_or_404(id)
    user = User.query.get(session['user_id'])
    if user.role == 'Employee' and consignment.branch_id != user.branch_id:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'id': consignment.id,
        'volume': consignment.volume,
        'destination': consignment.destination,
        'status': consignment.status,
        'charge': consignment.charge
    })

@app.route('/trucks', methods=['GET'])
@login_required()
def get_trucks():
    user = User.query.get(session['user_id'])
    query = Truck.query
    if user.role == 'Employee':
        query = query.filter_by(branch_id=user.branch_id)
    trucks = query.all()
    return jsonify([{
        'id': t.id,
        'location': t.location,
        'status': t.status,
        'last_updated': t.last_updated.isoformat()
    } for t in trucks])

@app.route('/reports/usage', methods=['GET'])
@login_required(role='Manager')
def truck_usage():
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)
    trucks = Truck.query.all()
    usage = []
    for truck in trucks:
        consignments = Consignment.query.join(ConsignmentTruck).filter(
            ConsignmentTruck.truck_id == truck.id,
            Consignment.dispatched_at >= start_date
        ).all()
        usage.append({
            'truck_id': truck.id,
            'consignments_handled': len(consignments),
            'total_volume': sum(c.volume for c in consignments)
        })
    return jsonify(usage)

@app.route('/reports/consignments', methods=['GET'])
@login_required(role='Manager')
def consignment_report():
    destination = request.args.get('destination')
    query = Consignment.query
    if destination:
        query = query.filter_by(destination=destination)
    consignments = query.all()
    return jsonify({
        'total_volume': sum(c.volume for c in consignments),
        'total_revenue': sum(c.charge for c in consignments),
        'count': len(consignments)
    })

@app.route('/reports/waiting', methods=['GET'])
@login_required(role='Manager')
def waiting_report():
    consignments = Consignment.query.filter(Consignment.status == 'Dispatched').all()
    waiting_times = [
        (c.dispatched_at - c.created_at).total_seconds() / 3600
        for c in consignments if c.dispatched_at
    ]
    avg_waiting = sum(waiting_times) / len(waiting_times) if waiting_times else 0
    trucks = Truck.query.filter_by(status='Available').all()
    idle_times = [
        (datetime.utcnow() - t.last_updated).total_seconds() / 3600
        for t in trucks
    ]
    avg_idle = sum(idle_times) / len(idle_times) if idle_times else 0
    return jsonify({
        'avg_waiting_time_hours': avg_waiting,
        'avg_idle_time_hours': avg_idle
    })

@app.route('/employees', methods=['POST'])
@login_required(role='Manager')
def add_employee():
    data = request.json
    if not data.get('username') or not data.get('password') or not data.get('branch_id'):
        return jsonify({'error': 'Username, password, and branch_id required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    if not Branch.query.get(data['branch_id']):
        return jsonify({'error': 'Invalid branch_id'}), 400
    hashed_pwd = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    employee = User(
        username=data['username'],
        password=hashed_pwd.decode('utf-8'),
        role='Employee',
        branch_id=data['branch_id']
    )
    db.session.add(employee)
    db.session.commit()
    return jsonify({'message': 'Employee added successfully'}), 201

@app.route('/branches', methods=['POST'])
@login_required(role='Manager')
def add_branch():
    data = request.json
    if not data.get('location'):
        return jsonify({'error': 'Location required'}), 400
    if Branch.query.filter_by(location=data['location']).first():
        return jsonify({'error': 'Branch location already exists'}), 400
    branch = Branch(location=data['location'])
    db.session.add(branch)
    db.session.commit()
    return jsonify({'message': 'Branch added successfully', 'branch_id': branch.id}), 201

@app.route('/trucks', methods=['POST'])
@login_required(role='Manager')
def add_truck():
    data = request.json
    if not data.get('location') or not data.get('branch_id'):
        return jsonify({'error': 'Location and branch_id required'}), 400
    if not Branch.query.get(data['branch_id']):
        return jsonify({'error': 'Invalid branch_id'}), 400
    truck = Truck(
        location=data['location'],
        branch_id=data['branch_id']
    )
    db.session.add(truck)
    db.session.commit()
    return jsonify({'message': 'Truck added successfully', 'truck_id': truck.id}), 201

# Initialize Database
with app.app_context():
    db.create_all()
    if not Branch.query.first():
        branches = ['Capital', 'CityA', 'CityB']
        for loc in branches:
            branch = Branch(location=loc)
            db.session.add(branch)
            db.session.commit()
            for _ in range(2):
                db.session.add(Truck(location=loc, branch_id=branch.id))
        db.session.commit()
    if not User.query.first():
        hashed_pwd = bcrypt.hashpw('managerpass'.encode('utf-8'), bcrypt.gensalt())
        db.session.add(User(username='manager1', password=hashed_pwd.decode('utf-8'), role='Manager'))
        branch = Branch.query.filter_by(location='CityA').first()
        hashed_pwd = bcrypt.hashpw('employeepass'.encode('utf-8'), bcrypt.gensalt())
        db.session.add(User(username='employee1', password=hashed_pwd.decode('utf-8'), role='Employee', branch_id=branch.id))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)