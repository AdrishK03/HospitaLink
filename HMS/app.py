from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# --- PostgreSQL Libraries ---
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURATION & INITIALIZATION ---

app = Flask(__name__)
load_dotenv() 

# IMPORTANT: Read variables from environment
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_safety')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Read database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_EMAIL = 'admin@hospital.com'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# --- DATABASE CONNECTION & SETUP FUNCTIONS ---

# Fix Render's "postgres://" format for psycopg2
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    """Establish and return a new PostgreSQL database connection."""
    if not DATABASE_URL:
        raise EnvironmentError("DATABASE_URL not set. Cannot connect to PostgreSQL.")
        
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    """Initialize all tables and create default admin if missing. Executed by entrypoint.sh."""
    conn = get_db()
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            specialization TEXT,
            contact TEXT,
            approved INTEGER DEFAULT 0
        )
    ''')

    # Appointments Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Medical Records Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medical_records (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            diagnosis TEXT,
            prescription TEXT,
            report_filename TEXT,
            date TEXT NOT NULL
        )
    ''')

    # Billing Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            appointment_id INTEGER,
            description TEXT,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            date TEXT NOT NULL
        )
    ''')

    # Create Default Admin (if not exists)
    c.execute("SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,))
    if not c.fetchone():
        admin_password = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO users (name, email, password, role, approved) VALUES (%s, %s, %s, %s, %s)",
            ('Admin', ADMIN_EMAIL, admin_password, 'admin', 1)
        )

    conn.commit()
    conn.close()


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
        
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = %s AND role = %s', (email, role))
            user = c.fetchone()
            conn.close()
        except EnvironmentError:
            flash('Database configuration error. Contact admin.', 'danger')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"DB Runtime Error on login: {e}")
            flash('Internal server error during login. Check server logs.', 'danger')
            return redirect(url_for('login'))
        
        if user and check_password_hash(user['password'], password):
            if role == 'doctor' and user['approved'] == 0:
                flash('Your account is pending approval from admin.', 'warning')
                return redirect(url_for('login'))
            
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            
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
        
        # --- FIX: Prevent registering as Admin ---
        if role == 'admin' or email == ADMIN_EMAIL:
            flash('Cannot register with the admin role or admin email.', 'danger')
            return redirect(url_for('register'))
        # ----------------------------------------
        
        conn = get_db()
        c = conn.cursor()
        try:
            # Check if email exists
            c.execute("SELECT id FROM users WHERE email = %s", (email,))
            if c.fetchone():
                 flash('Email already exists!', 'danger')
                 conn.close()
                 return redirect(url_for('register'))
                 
            approved = 1 if role == 'patient' else 0
            
            c.execute(
                "INSERT INTO users (name, email, password, role, specialization, contact, approved) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, email, password, role, specialization, contact, approved)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            if role == 'doctor':
                flash('Your account will be activated after admin approval.', 'info')
            conn.close()
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Email already exists!', 'danger')
            conn.close()
        except Exception as e:
            conn.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
            conn.close()
    
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
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE role = %s', ('doctor',))
    doctors = c.fetchall()
    
    c.execute('SELECT * FROM users WHERE role = %s', ('patient',))
    patients = c.fetchall()
    
    c.execute('''SELECT a.*, p.name as patient_name, d.name as doctor_name 
                 FROM appointments a 
                 JOIN users p ON a.patient_id = p.id 
                 JOIN users d ON a.doctor_id = d.id 
                 ORDER BY a.date DESC''')
    appointments = c.fetchall()
                                
    c.execute('''SELECT b.*, p.name as patient_name, d.name as doctor_name 
                FROM billing b 
                JOIN users p ON b.patient_id = p.id 
                JOIN users d ON b.doctor_id = d.id 
                ORDER BY b.date DESC''')
    billing = c.fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, 
                           appointments=appointments, billing=billing)

@app.route('/admin/approve_doctor/<int:doctor_id>')
def approve_doctor(doctor_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET approved = 1 WHERE id = %s', (doctor_id,))
    conn.commit()
    conn.close()
    flash('Doctor approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Doctor Routes
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    doctor_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT a.*, p.name as patient_name, p.contact 
                 FROM appointments a 
                 JOIN users p ON a.patient_id = p.id 
                 WHERE a.doctor_id = %s 
                 ORDER BY a.date DESC''', (doctor_id,))
    appointments = c.fetchall()
    conn.close()
    
    return render_template('doctor_dashboard.html', appointments=appointments)

@app.route('/doctor/update_appointment/<int:appointment_id>/<status>')
def update_appointment_status(appointment_id, status):
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE appointments SET status = %s WHERE id = %s', (status, appointment_id))
    conn.commit()
    conn.close()
    flash(f'Appointment {status.lower()} successfully!', 'success')
    return redirect(url_for('doctor_dashboard'))

# Patient Routes
@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['user_role'] != 'patient':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    patient_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE role = %s AND approved = 1', ('doctor',))
    doctors = c.fetchall()
    c.execute('''SELECT a.*, d.name as doctor_name, d.specialization 
                 FROM appointments a 
                 JOIN users d ON a.doctor_id = d.id 
                 WHERE a.patient_id = %s 
                 ORDER BY a.date DESC''', (patient_id,))
    appointments = c.fetchall()
    conn.close()
    
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments)

# Appointments Routes - FIXED
@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    
    if request.method == 'POST':
        patient_id = session['user_id']
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']
        reason = request.form['reason']
        
        conn = None
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT INTO appointments (patient_id, doctor_id, date, time, reason) VALUES (%s, %s, %s, %s, %s)",
                (patient_id, doctor_id, date, time, reason)
            )
            conn.commit()
            conn.close()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('appointments'))
        except Exception as e:
            if conn:
                conn.close()
            print(f"Error booking appointment: {e}")
            flash(f'Error booking appointment: {str(e)}', 'danger')
            return redirect(url_for('appointments'))
    
    # GET request - show appointments page
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        if role == 'patient':
            c.execute('''SELECT a.*, d.name as doctor_name, d.specialization 
                         FROM appointments a 
                         JOIN users d ON a.doctor_id = d.id 
                         WHERE a.patient_id = %s 
                         ORDER BY a.date DESC, a.time DESC''', (user_id,))
            appointments_list = c.fetchall()
            
            # FIX: Always fetch doctors list for patients
            c.execute('SELECT * FROM users WHERE role = %s AND approved = 1', ('doctor',))
            doctors = c.fetchall()
            conn.close()
            return render_template('appointments.html', appointments=appointments_list, doctors=doctors)
        
        elif role == 'doctor':
            c.execute('''SELECT a.*, p.name as patient_name, p.contact 
                         FROM appointments a 
                         JOIN users p ON a.patient_id = p.id 
                         WHERE a.doctor_id = %s 
                         ORDER BY a.date DESC, a.time DESC''', (user_id,))
            appointments_list = c.fetchall()
            conn.close()
            return render_template('appointments.html', appointments=appointments_list)
            
        else:  # admin
            c.execute('''SELECT a.*, p.name as patient_name, d.name as doctor_name 
                         FROM appointments a 
                         JOIN users p ON a.patient_id = p.id 
                         JOIN users d ON a.doctor_id = d.id 
                         ORDER BY a.date DESC, a.time DESC''')
            appointments_list = c.fetchall()
            conn.close()
            return render_template('appointments.html', appointments=appointments_list)
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error fetching appointments: {e}")
        flash(f'Error loading appointments: {str(e)}', 'danger')
        if role == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        else:
            return redirect(url_for('admin_dashboard'))

# Patient cancel appointment route - FIXED
@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session['user_role'] != 'patient':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Verify the appointment belongs to the logged-in patient
        c.execute('SELECT id FROM appointments WHERE id = %s AND patient_id = %s', 
                  (appointment_id, session['user_id']))
        appointment = c.fetchone()
        
        if appointment:
            c.execute('UPDATE appointments SET status = %s WHERE id = %s', ('Cancelled', appointment_id))
            conn.commit()
            flash('Appointment cancelled successfully!', 'success')
        else:
            flash('Appointment not found or access denied!', 'danger')
        
        conn.close()
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error cancelling appointment: {e}")
        flash(f'Error cancelling appointment: {str(e)}', 'danger')
    
    # FIX: Check if request came from appointments page or dashboard
    referrer = request.referrer
    if referrer and '/appointments' in referrer:
        return redirect(url_for('appointments'))
    else:
        return redirect(url_for('patient_dashboard'))

# Medical Records Routes
@app.route('/medical_records')
def medical_records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    conn = None
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        if role == 'patient':
            c.execute('''SELECT m.*, d.name as doctor_name 
                         FROM medical_records m 
                         JOIN users d ON m.doctor_id = d.id 
                         WHERE m.patient_id = %s 
                         ORDER BY m.date DESC''', (user_id,))
            records = c.fetchall()
            conn.close()
            return render_template('medical_records.html', records=records)
            
        elif role == 'doctor':
            c.execute('''SELECT m.*, p.name as patient_name 
                         FROM medical_records m 
                         JOIN users p ON m.patient_id = p.id 
                         WHERE m.doctor_id = %s 
                         ORDER BY m.date DESC''', (user_id,))
            records = c.fetchall()
            
            c.execute('''SELECT DISTINCT p.* FROM users p 
                         JOIN appointments a ON p.id = a.patient_id 
                         WHERE a.doctor_id = %s''', (user_id,))
            patients = c.fetchall()
            conn.close()
            return render_template('medical_records.html', records=records, patients=patients)
            
        else: # admin
            c.execute('''SELECT m.*, p.name as patient_name, d.name as doctor_name 
                         FROM medical_records m 
                         JOIN users p ON m.patient_id = p.id 
                         JOIN users d ON m.doctor_id = d.id 
                         ORDER BY m.date DESC''')
            records = c.fetchall()
            conn.close()
            return render_template('medical_records.html', records=records)
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error fetching medical records: {e}")
        flash(f'Error loading medical records: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))

@app.route('/add_medical_record', methods=['POST'])
def add_medical_record():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    
    doctor_id = session['user_id']
    patient_id = request.form['patient_id']
    diagnosis = request.form['diagnosis']
    prescription = request.form['prescription']
    date = datetime.now().strftime('%Y-%m-%d')
    
    report_filename = None
    if 'report' in request.files:
        file = request.files['report']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            report_filename = filename
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO medical_records (patient_id, doctor_id, diagnosis, prescription, report_filename, date) VALUES (%s, %s, %s, %s, %s, %s)",
            (patient_id, doctor_id, diagnosis, prescription, report_filename, date)
        )
        conn.commit()
        flash('Medical record added successfully!', 'success')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error adding medical record: {e}")
        flash(f'Error adding medical record: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('medical_records'))

# Billing Routes
@app.route('/billing')
def billing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    conn = None
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        if role == 'patient':
            c.execute('''SELECT b.*, d.name as doctor_name 
                         FROM billing b 
                         JOIN users d ON b.doctor_id = d.id 
                         WHERE b.patient_id = %s 
                         ORDER BY b.date DESC''', (user_id,))
            bills = c.fetchall()
            conn.close()
            return render_template('billing.html', bills=bills)
                                 
        elif role == 'doctor':
            c.execute('''SELECT b.*, p.name as patient_name 
                         FROM billing b 
                         JOIN users p ON b.patient_id = p.id 
                         WHERE b.doctor_id = %s 
                         ORDER BY b.date DESC''', (user_id,))
            bills = c.fetchall()
            conn.close()
            return render_template('billing.html', bills=bills)
                                 
        else: # admin
            c.execute('''SELECT b.*, p.name as patient_name, d.name as doctor_name 
                         FROM billing b 
                         JOIN users p ON b.patient_id = p.id 
                         JOIN users d ON b.doctor_id = d.id 
                         ORDER BY b.date DESC''')
            bills = c.fetchall()
            
            c.execute('SELECT * FROM users WHERE role = %s', ('patient',))
            patients = c.fetchall()
            
            c.execute('SELECT * FROM users WHERE role = %s AND approved = 1', ('doctor',))
            doctors = c.fetchall()
            conn.close()
            return render_template('billing.html', bills=bills, patients=patients, doctors=doctors)
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error fetching billing: {e}")
        flash(f'Error loading billing: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))

@app.route('/add_bill', methods=['POST'])
def add_bill():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    patient_id = request.form['patient_id']
    doctor_id = request.form['doctor_id']
    description = request.form['description']
    total_amount = request.form['total_amount']
    date = datetime.now().strftime('%Y-%m-%d')
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO billing (patient_id, doctor_id, description, total_amount, date) VALUES (%s, %s, %s, %s, %s)",
            (patient_id, doctor_id, description, total_amount, date)
        )
        conn.commit()
        flash('Bill created successfully!', 'success')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error adding bill: {e}")
        flash(f'Error creating bill: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('billing'))

@app.route('/update_bill_status/<int:bill_id>/<status>')
def update_bill_status(bill_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE billing SET status = %s WHERE id = %s', (status, bill_id))
        conn.commit()
        flash('Bill status updated!', 'success')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating bill: {e}")
        flash(f'Error updating bill status: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('billing'))

if __name__ == '__main__':
    # Initialize DB for local testing
    try:
        if DATABASE_URL:
            init_db()
        else:
            print("WARNING: DATABASE_URL not set. Running locally without DB initialization.")
    except Exception as e:
        print(f"FATAL ERROR during local DB initialization: {e}")
        
    app.run(debug=True)
