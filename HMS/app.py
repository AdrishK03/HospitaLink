from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import or_ # func is not needed in the final queries, so removing it for cleanup

app = Flask(__name__)
load_dotenv()

# --- CONFIGURATION ---
# IMPORTANT: Reads SECRET_KEY and DATABASE_URL from environment variables for production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hospital.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# --- DATABASE MODELS (SQLAlchemy ORM) ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False) # 'admin', 'doctor', 'patient'
    specialization = db.Column(db.Text)
    contact = db.Column(db.Text)
    approved = db.Column(db.Integer, default=0) # 0=Pending, 1=Approved

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Text, nullable=False)
    time = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.Text, default='Pending')

    patient = db.relationship('User', foreign_keys=[patient_id], backref='patient_appointments')
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='doctor_appointments')

class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    report_filename = db.Column(db.Text)
    date = db.Column(db.Text, nullable=False)

class Billing(db.Model):
    __tablename__ = 'billing'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    description = db.Column(db.Text)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Text, default='Unpaid')
    date = db.Column(db.Text, nullable=False)

# --- DATABASE SETUP FUNCTION ---

def setup_database():
    """Initializes the database schema and creates the default admin user."""
    # This must be run inside an application context
    with app.app_context(): 
        db.create_all()

        # Create default admin if not exists
        if not User.query.filter_by(email='admin@hospital.com').first():
            admin_password = generate_password_hash('admin123')
            admin_user = User(name='Admin', email='admin@hospital.com', password=admin_password, role='admin', approved=1)
            db.session.add(admin_user)
            db.session.commit()

# --- ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        user = User.query.filter_by(email=email, role=role).first()
        
        if user and check_password_hash(user.password, password):
            if role == 'doctor' and user.approved == 0:
                flash('Your account is pending approval from admin.', 'warning')
                return redirect(url_for('login'))
            
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        contact = request.form['contact']
        specialization = request.form.get('specialization', '')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        approved = 1 if role == 'patient' else 0
        new_user = User(
            name=name, email=email, password=password, role=role,
            specialization=specialization, contact=contact, approved=approved
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        if role == 'doctor':
            flash('Your account will be activated after admin approval.', 'info')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    # ORM Queries for Admin Dashboard
    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    
    # NOTE: The Appointment query uses direct column names for clarity in the template
    appointments = db.session.query(
        Appointment, User.name.label('patient_name'), User.name.label('doctor_name')
    ).join(User, Appointment.patient_id == User.id).all()
    
    billing = Billing.query.all()
    
    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, 
                           appointments=appointments, billing=billing)

@app.route('/admin/approve_doctor/<int:doctor_id>')
def approve_doctor(doctor_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(doctor_id)
    user.approved = 1
    db.session.commit()
    
    flash('Doctor approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Doctor Routes
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    doctor_id = session['user_id']
    
    # ORM Query with JOINs
    appointments = db.session.query(
        Appointment, User.name.label('patient_name'), User.contact.label('contact')
    ).join(User, Appointment.patient_id == User.id)\
     .filter(Appointment.doctor_id == doctor_id)\
     .order_by(Appointment.date.desc()).all()
    
    return render_template('doctor_dashboard.html', appointments=appointments)

@app.route('/doctor/update_appointment/<int:appointment_id>/<status>')
def update_appointment_status(appointment_id, status):
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()
    
    flash(f'Appointment {status.lower()} successfully!', 'success')
    return redirect(url_for('doctor_dashboard'))

# Patient Routes
@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['user_role'] != 'patient':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    patient_id = session['user_id']
    
    # ORM Queries
    doctors = User.query.filter_by(role='doctor', approved=1).all()
    
    appointments = db.session.query(
        Appointment, User.name.label('doctor_name'), User.specialization.label('specialization')
    ).join(User, Appointment.doctor_id == User.id)\
     .filter(Appointment.patient_id == patient_id)\
     .order_by(Appointment.date.desc()).all()
    
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments)

# Appointments Routes (Used by all roles)
@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']

    if request.method == 'POST':
        # Booking logic
        new_appointment = Appointment(
            patient_id=user_id,
            doctor_id=request.form['doctor_id'],
            date=request.form['date'],
            time=request.form['time'],
            reason=request.form['reason']
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments'))
    
    # GET request - show appointments page
    
    if role == 'patient':
        appointments_list = db.session.query(
            Appointment, User.name.label('doctor_name'), User.specialization.label('specialization')
        ).join(User, Appointment.doctor_id == User.id)\
         .filter(Appointment.patient_id == user_id)\
         .order_by(Appointment.date.desc(), Appointment.time.desc()).all()
        
        doctors = User.query.filter_by(role='doctor', approved=1).all()
        return render_template('appointments.html', appointments=appointments_list, doctors=doctors)
        
    elif role == 'doctor':
        appointments_list = db.session.query(
            Appointment, User.name.label('patient_name'), User.contact.label('contact')
        ).join(User, Appointment.patient_id == User.id)\
         .filter(Appointment.doctor_id == user_id)\
         .order_by(Appointment.date.desc(), Appointment.time.desc()).all()
        
        return render_template('appointments.html', appointments=appointments_list)
        
    else:  # admin
        # Simplified query for Admin view
        appointments_list = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
        
        return render_template('appointments.html', appointments=appointments_list)


# Medical Records Routes
@app.route('/medical_records')
def medical_records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']

    if role == 'patient':
        records = db.session.query(
            MedicalRecord, User.name.label('doctor_name')
        ).join(User, MedicalRecord.doctor_id == User.id)\
         .filter(MedicalRecord.patient_id == user_id)\
         .order_by(MedicalRecord.date.desc()).all()
        return render_template('medical_records.html', records=records)
        
    elif role == 'doctor':
        records = db.session.query(
            MedicalRecord, User.name.label('patient_name')
        ).join(User, MedicalRecord.patient_id == User.id)\
         .filter(MedicalRecord.doctor_id == user_id)\
         .order_by(MedicalRecord.date.desc()).all()
         
        patients = db.session.query(User).join(Appointment, User.id == Appointment.patient_id)\
                   .filter(Appointment.doctor_id == user_id).distinct().all()
        
        return render_template('medical_records.html', records=records, patients=patients)
        
    else: # admin
        records = MedicalRecord.query.order_by(MedicalRecord.date.desc()).all()
        return render_template('medical_records.html', records=records)

@app.route('/add_medical_record', methods=['POST'])
def add_medical_record():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    
    doctor_id = session['user_id']
    
    report_filename = None
    if 'report' in request.files:
        file = request.files['report']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            report_filename = filename
    
    new_record = MedicalRecord(
        patient_id=request.form['patient_id'],
        doctor_id=doctor_id,
        diagnosis=request.form['diagnosis'],
        prescription=request.form['prescription'],
        report_filename=report_filename,
        date=datetime.now().strftime('%Y-%m-%d')
    )
    db.session.add(new_record)
    db.session.commit()
    
    flash('Medical record added successfully!', 'success')
    return redirect(url_for('medical_records'))


# Billing Routes
@app.route('/billing')
def billing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    
    if role == 'patient':
        bills = db.session.query(Billing, User.name.label('doctor_name'))\
                .join(User, Billing.doctor_id == User.id)\
                .filter(Billing.patient_id == user_id).order_by(Billing.date.desc()).all()
        
    elif role == 'doctor':
        bills = db.session.query(Billing, User.name.label('patient_name'))\
                .join(User, Billing.patient_id == User.id)\
                .filter(Billing.doctor_id == user_id).order_by(Billing.date.desc()).all()
        
    else: # admin
        bills = Billing.query.order_by(Billing.date.desc()).all()
        patients = User.query.filter_by(role='patient').all()
        doctors = User.query.filter_by(role='doctor', approved=1).all()
        return render_template('billing.html', bills=bills, patients=patients, doctors=doctors)
    
    return render_template('billing.html', bills=bills)

@app.route('/add_bill', methods=['POST'])
def add_bill():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    new_bill = Billing(
        patient_id=request.form['patient_id'],
        doctor_id=request.form['doctor_id'],
        description=request.form['description'],
        total_amount=request.form['total_amount'],
        date=datetime.now().strftime('%Y-%m-%d')
    )
    db.session.add(new_bill)
    db.session.commit()
    
    flash('Bill created successfully!', 'success')
    return redirect(url_for('billing'))

@app.route('/update_bill_status/<int:bill_id>/<status>')
def update_bill_status(bill_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    bill = Billing.query.get_or_404(bill_id)
    bill.status = status
    db.session.commit()
    
    flash('Bill status updated!', 'success')
    return redirect(url_for('billing'))

@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_role' not in session or session['user_role'] != 'patient':
        return redirect('/login')

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'Cancelled'
    db.session.commit()

    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('appointments'))


if __name__ == '__main__':
    # Run setup locally when running app.py directly
    setup_database()
    app.run(debug=True)
