from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_in_production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        specialization TEXT,
        contact TEXT,
        approved INTEGER DEFAULT 0
    )''')
    
    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (patient_id) REFERENCES users(id),
        FOREIGN KEY (doctor_id) REFERENCES users(id)
    )''')
    
    # Medical records table
    c.execute('''CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        diagnosis TEXT,
        prescription TEXT,
        report_filename TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES users(id),
        FOREIGN KEY (doctor_id) REFERENCES users(id)
    )''')
    
    # Billing table
    c.execute('''CREATE TABLE IF NOT EXISTS billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appointment_id INTEGER,
        description TEXT,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Unpaid',
        date TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES users(id),
        FOREIGN KEY (doctor_id) REFERENCES users(id),
        FOREIGN KEY (appointment_id) REFERENCES appointments(id)
    )''')
    
    # Create default admin if not exists
    c.execute("SELECT * FROM users WHERE email = 'admin@hospital.com'")
    if not c.fetchone():
        admin_password = generate_password_hash('admin123')
        c.execute("INSERT INTO users (name, email, password, role, approved) VALUES (?, ?, ?, ?, ?)",
                  ('Admin', 'admin@hospital.com', admin_password, 'admin', 1))
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper function to get database connection
def get_db():
    conn = sqlite3.connect('hospital.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND role = ?', (email, role)).fetchone()
        conn.close()
        
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
        
        conn = get_db()
        try:
            approved = 1 if role == 'patient' else 0
            conn.execute('INSERT INTO users (name, email, password, role, specialization, contact, approved) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (name, email, password, role, specialization, contact, approved))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            if role == 'doctor':
                flash('Your account will be activated after admin approval.', 'info')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'danger')
        finally:
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
    doctors = conn.execute('SELECT * FROM users WHERE role = "doctor"').fetchall()
    patients = conn.execute('SELECT * FROM users WHERE role = "patient"').fetchall()
    appointments = conn.execute('''SELECT a.*, 
        p.name as patient_name, d.name as doctor_name 
        FROM appointments a 
        JOIN users p ON a.patient_id = p.id 
        JOIN users d ON a.doctor_id = d.id 
        ORDER BY a.date DESC''').fetchall()
    billing = conn.execute('''SELECT b.*, 
        p.name as patient_name, d.name as doctor_name 
        FROM billing b 
        JOIN users p ON b.patient_id = p.id 
        JOIN users d ON b.doctor_id = d.id 
        ORDER BY b.date DESC''').fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', doctors=doctors, patients=patients, 
                         appointments=appointments, billing=billing)

@app.route('/admin/approve_doctor/<int:doctor_id>')
def approve_doctor(doctor_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('UPDATE users SET approved = 1 WHERE id = ?', (doctor_id,))
    conn.commit()
    conn.close()
    flash('Doctor approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
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
    appointments = conn.execute('''SELECT a.*, p.name as patient_name, p.contact 
        FROM appointments a 
        JOIN users p ON a.patient_id = p.id 
        WHERE a.doctor_id = ? 
        ORDER BY a.date DESC''', (doctor_id,)).fetchall()
    conn.close()
    
    return render_template('doctor_dashboard.html', appointments=appointments)

@app.route('/doctor/update_appointment/<int:appointment_id>/<status>')
def update_appointment_status(appointment_id, status):
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('UPDATE appointments SET status = ? WHERE id = ?', (status, appointment_id))
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
    doctors = conn.execute('SELECT * FROM users WHERE role = "doctor" AND approved = 1').fetchall()
    appointments = conn.execute('''SELECT a.*, d.name as doctor_name, d.specialization 
        FROM appointments a 
        JOIN users d ON a.doctor_id = d.id 
        WHERE a.patient_id = ? 
        ORDER BY a.date DESC''', (patient_id,)).fetchall()
    conn.close()
    
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments)

# Appointments Routes
@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        patient_id = session['user_id']
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']
        reason = request.form['reason']
        
        conn = get_db()
        conn.execute('INSERT INTO appointments (patient_id, doctor_id, date, time, reason) VALUES (?, ?, ?, ?, ?)',
                    (patient_id, doctor_id, date, time, reason))
        conn.commit()
        conn.close()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments'))
    
    # GET request - show appointments page
    user_id = session['user_id']
    role = session['user_role']
    conn = get_db()
    
    if role == 'patient':
        appointments_list = conn.execute('''SELECT a.*, d.name as doctor_name, d.specialization 
            FROM appointments a 
            JOIN users d ON a.doctor_id = d.id 
            WHERE a.patient_id = ? 
            ORDER BY a.date DESC, a.time DESC''', (user_id,)).fetchall()
        doctors = conn.execute('SELECT * FROM users WHERE role = "doctor" AND approved = 1').fetchall()
        conn.close()
        return render_template('appointments.html', appointments=appointments_list, doctors=doctors)
    elif role == 'doctor':
        appointments_list = conn.execute('''SELECT a.*, p.name as patient_name, p.contact 
            FROM appointments a 
            JOIN users p ON a.patient_id = p.id 
            WHERE a.doctor_id = ? 
            ORDER BY a.date DESC, a.time DESC''', (user_id,)).fetchall()
        conn.close()
        return render_template('appointments.html', appointments=appointments_list)
    else:  # admin
        appointments_list = conn.execute('''SELECT a.*, 
            p.name as patient_name, d.name as doctor_name 
            FROM appointments a 
            JOIN users p ON a.patient_id = p.id 
            JOIN users d ON a.doctor_id = d.id 
            ORDER BY a.date DESC, a.time DESC''').fetchall()
        conn.close()
        return render_template('appointments.html', appointments=appointments_list)

# Medical Records Routes
@app.route('/medical_records')
def medical_records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    conn = get_db()
    
    if role == 'patient':
        records = conn.execute('''SELECT m.*, d.name as doctor_name 
            FROM medical_records m 
            JOIN users d ON m.doctor_id = d.id 
            WHERE m.patient_id = ? 
            ORDER BY m.date DESC''', (user_id,)).fetchall()
    elif role == 'doctor':
        records = conn.execute('''SELECT m.*, p.name as patient_name 
            FROM medical_records m 
            JOIN users p ON m.patient_id = p.id 
            WHERE m.doctor_id = ? 
            ORDER BY m.date DESC''', (user_id,)).fetchall()
        patients = conn.execute('''SELECT DISTINCT p.* 
            FROM users p 
            JOIN appointments a ON p.id = a.patient_id 
            WHERE a.doctor_id = ?''', (user_id,)).fetchall()
        conn.close()
        return render_template('medical_records.html', records=records, patients=patients)
    else:
        records = conn.execute('''SELECT m.*, p.name as patient_name, d.name as doctor_name 
            FROM medical_records m 
            JOIN users p ON m.patient_id = p.id 
            JOIN users d ON m.doctor_id = d.id 
            ORDER BY m.date DESC''').fetchall()
    
    conn.close()
    return render_template('medical_records.html', records=records)

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
    
    conn = get_db()
    conn.execute('INSERT INTO medical_records (patient_id, doctor_id, diagnosis, prescription, report_filename, date) VALUES (?, ?, ?, ?, ?, ?)',
                (patient_id, doctor_id, diagnosis, prescription, report_filename, date))
    conn.commit()
    conn.close()
    flash('Medical record added successfully!', 'success')
    return redirect(url_for('medical_records'))

# Billing Routes
@app.route('/billing')
def billing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['user_role']
    conn = get_db()
    
    if role == 'patient':
        bills = conn.execute('''SELECT b.*, d.name as doctor_name 
            FROM billing b 
            JOIN users d ON b.doctor_id = d.id 
            WHERE b.patient_id = ? 
            ORDER BY b.date DESC''', (user_id,)).fetchall()
    elif role == 'doctor':
        bills = conn.execute('''SELECT b.*, p.name as patient_name 
            FROM billing b 
            JOIN users p ON b.patient_id = p.id 
            WHERE b.doctor_id = ? 
            ORDER BY b.date DESC''', (user_id,)).fetchall()
    else:
        bills = conn.execute('''SELECT b.*, p.name as patient_name, d.name as doctor_name 
            FROM billing b 
            JOIN users p ON b.patient_id = p.id 
            JOIN users d ON b.doctor_id = d.id 
            ORDER BY b.date DESC''').fetchall()
        patients = conn.execute('SELECT * FROM users WHERE role = "patient"').fetchall()
        doctors = conn.execute('SELECT * FROM users WHERE role = "doctor" AND approved = 1').fetchall()
        conn.close()
        return render_template('billing.html', bills=bills, patients=patients, doctors=doctors)
    
    conn.close()
    return render_template('billing.html', bills=bills)

@app.route('/add_bill', methods=['POST'])
def add_bill():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    patient_id = request.form['patient_id']
    doctor_id = request.form['doctor_id']
    description = request.form['description']
    total_amount = request.form['total_amount']
    date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    conn.execute('INSERT INTO billing (patient_id, doctor_id, description, total_amount, date) VALUES (?, ?, ?, ?, ?)',
                (patient_id, doctor_id, description, total_amount, date))
    conn.commit()
    conn.close()
    flash('Bill created successfully!', 'success')
    return redirect(url_for('billing'))

@app.route('/update_bill_status/<int:bill_id>/<status>')
def update_bill_status(bill_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('UPDATE billing SET status = ? WHERE id = ?', (status, bill_id))
    conn.commit()
    conn.close()
    flash('Bill status updated!', 'success')
    return redirect(url_for('billing'))

@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_role' not in session or session['user_role'] != 'patient':
        return redirect('/login')

    db = get_db()  # replace with your actual DB function
    db.execute('UPDATE appointments SET status = ? WHERE id = ?', ('Cancelled', appointment_id))
    db.commit()

    flash('Appointment cancelled successfully.', 'success')
    return redirect('/appointments')


if __name__ == '__main__':
    app.run(debug=True)