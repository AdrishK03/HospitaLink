# 🏥 Hospital Management System

A comprehensive web-based Hospital Management System built with Flask (Python) and PostgreSQL, featuring role-based access control for Admins, Doctors, and Patients.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [Features](#-features)
- [Demo](#-demo)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Deployment](#-deployment)
- [Screenshots](#-screenshots)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 👨‍💼 Admin Features
- ✅ Manage doctors (approve/edit/delete)
- ✅ Manage patients (view/edit/delete)
- ✅ View all appointments system-wide
- ✅ Generate and manage billing records
- ✅ Complete dashboard with statistics
- ✅ Edit user details (name, email, contact, specialization)

### 👨‍⚕️ Doctor Features
- ✅ View scheduled appointments
- ✅ Update appointment status (complete/cancel)
- ✅ Add medical records with prescriptions
- ✅ Upload patient reports (PDF, images)
- ✅ View billing information for patients
- ✅ Dashboard with appointment statistics

### 👤 Patient Features
- ✅ Register and book appointments with doctors
- ✅ View appointment history and status
- ✅ Access medical records and prescriptions
- ✅ View and pay bills
- ✅ Cancel pending appointments
- ✅ Update personal profile

## 🎬 Demo

**Live Demo:** [Your Render URL Here]

**Default Admin Credentials:**
- Email: `admin@hospital.com`
- Password: `admin123`

⚠️ **Please change admin credentials after first login!**

## 🛠️ Tech Stack

### Backend
- **Framework:** Flask (Python)
- **Database:** PostgreSQL
- **Authentication:** Session-based with password hashing (Werkzeug)
- **ORM:** psycopg2 with RealDictCursor

### Frontend
- **HTML5** with Jinja2 templating
- **CSS3** (Inline styling with modern gradients)
- **JavaScript** (Vanilla JS for interactivity)
- **Responsive Design** (Mobile-friendly)

### Key Libraries
- Flask
- psycopg2-binary
- python-dotenv
- Werkzeug

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hospital-management-system.git
   cd hospital-management-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file**
   ```bash
   touch .env
   ```

5. **Configure environment variables**
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/hospital_db
   SECRET_KEY=your-secret-key-here
   ```

6. **Initialize database**
   ```bash
   python app.py
   ```
   The database will be automatically initialized on first run.

7. **Access the application**
   ```
   Open browser: http://127.0.0.1:5000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
DATABASE_URL=postgresql://user:password@host:port/database

# Optional (auto-generated if not provided)
SECRET_KEY=your-super-secret-key-change-in-production
```

### Database Configuration

The application automatically creates the following tables:
- `users` - Stores all system users (admin, doctors, patients)
- `appointments` - Manages patient appointments
- `medical_records` - Stores patient medical history
- `billing` - Handles billing and payments

All tables use CASCADE DELETE for referential integrity.

## 🚀 Usage

### First Time Setup

1. **Run the application**
   ```bash
   python app.py
   ```

2. **Login as Admin**
   - Navigate to `http://localhost:5000`
   - Use default credentials (see Demo section)
   - **Change password immediately!**

3. **Register Users**
   - Patients can self-register (automatically approved)
   - Doctors can register (requires admin approval)

### User Workflows

#### Admin Workflow
1. Login → Admin Dashboard
2. Approve pending doctor registrations
3. Edit user details (doctors/patients)
4. View all appointments and records
5. Generate bills for patients

#### Doctor Workflow
1. Register → Wait for admin approval
2. Login → Doctor Dashboard
3. View scheduled appointments
4. Complete/Cancel appointments
5. Add medical records and prescriptions
6. Upload patient reports

#### Patient Workflow
1. Register → Auto-approved
2. Login → Patient Dashboard
3. Book appointments with available doctors
4. View appointment status
5. Access medical records
6. View and pay bills

## 📁 Project Structure

```
hospital-management-system/
│
├── app.py                      # Main Flask application
├── database.py                 # Database configuration and setup
├── .env                        # Environment variables (create this)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── templates/                  # HTML templates
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── admin_dashboard.html   # Admin dashboard
│   ├── doctor_dashboard.html  # Doctor dashboard
│   ├── patient_dashboard.html # Patient dashboard
│   ├── appointments.html      # Appointments management
│   ├── medical_records.html   # Medical records page
│   └── billing.html           # Billing and payments
│
└── static/
    └── uploads/               # Uploaded medical reports
```

## 🌐 Deployment

### Deploy to Render

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/hospital-management-system.git
   git push -u origin main
   ```

2. **Create PostgreSQL Database on Render**
   - Dashboard → New + → PostgreSQL
   - Choose Free tier
   - Note the Internal Database URL

3. **Create Web Service on Render**
   - Dashboard → New + → Web Service
   - Connect your GitHub repository
   - Configure:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python app.py`
   - Add Environment Variables:
     - `DATABASE_URL` = Your Render PostgreSQL Internal URL
     - `SECRET_KEY` = Generate a strong random key

4. **Deploy**
   - Render will automatically deploy
   - Database initializes on first run
   - Access your live URL!

### Deploy to Heroku

```bash
# Install Heroku CLI
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

### Deploy to Railway

```bash
# Install Railway CLI
railway login
railway init
railway add postgres
railway up
```

## 📸 Screenshots

### Login Page
![Login](screenshots/login.png)

### Admin Dashboard
![Admin Dashboard](screenshots/admin.png)

### Doctor Dashboard
![Doctor Dashboard](screenshots/doctor.png)

### Patient Dashboard
![Patient Dashboard](screenshots/patient.png)

### Appointments Management
![Appointments](screenshots/appointments.png)

## 🔒 Security Features

- ✅ Password hashing using Werkzeug
- ✅ Session-based authentication
- ✅ Role-based access control (RBAC)
- ✅ SQL injection prevention (parameterized queries)
- ✅ CSRF protection ready
- ✅ Secure file uploads with filename sanitization
- ✅ Admin cannot delete their own account
- ✅ Email uniqueness validation
- ✅ Prevents unauthorized access to routes

## 🧪 Testing

### Run Tests Locally

```bash
# Create test database
createdb hospital_test

# Run tests (if test suite is added)
python -m pytest tests/
```

### Manual Testing Checklist

- [ ] Admin can login
- [ ] Admin can approve doctors
- [ ] Admin can edit user details
- [ ] Admin can delete users
- [ ] Doctor can view appointments
- [ ] Doctor can add medical records
- [ ] Patient can book appointments
- [ ] Patient can cancel appointments
- [ ] Patient can view medical records
- [ ] Billing works for all roles

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Contribution Guidelines

- Follow PEP 8 style guide for Python code
- Write clear commit messages
- Add comments to complex logic
- Update documentation as needed
- Test thoroughly before submitting PR

## 🐛 Bug Reports

Found a bug? Please open an issue with:
- Clear description of the bug
- Steps to reproduce
- Expected behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, etc.)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

## 🙏 Acknowledgments

- Flask documentation and community
- PostgreSQL documentation
- Render for hosting
- All contributors and testers

## 📞 Support

For support, email your-email@example.com or open an issue on GitHub.

## 🗺️ Roadmap

### Version 2.0 (Planned)
- [ ] Email notifications for appointments
- [ ] SMS reminders
- [ ] Doctor availability calendar
- [ ] Online payment integration
- [ ] Prescription PDF generation
- [ ] Advanced search and filters
- [ ] Patient medical history timeline
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Mobile app (React Native)

## 📊 Database Schema

```sql
users (id, name, email, password, role, specialization, contact, approved)
appointments (id, patient_id, doctor_id, date, time, reason, status)
medical_records (id, patient_id, doctor_id, diagnosis, prescription, report_filename, date)
billing (id, patient_id, doctor_id, appointment_id, description, total_amount, status, date)
```

## 🔧 Troubleshooting

### Common Issues

**Issue:** Database connection error
```bash
Solution: Check DATABASE_URL in .env file
```

**Issue:** Module not found
```bash
Solution: pip install -r requirements.txt
```

**Issue:** Delete user fails
```bash
Solution: Ensure foreign key constraints have CASCADE DELETE
```

**Issue:** Port already in use
```bash
Solution: Change port in app.py or kill process using port 5000
```

## 📚 Documentation

For detailed documentation, visit:
- [User Guide](docs/USER_GUIDE.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [API Documentation](docs/API.md)

## ⭐ Star History

If you find this project useful, please consider giving it a star!

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/hospital-management-system&type=Date)](https://star-history.com/#yourusername/hospital-management-system&Date)

---

**Made with ❤️ for healthcare management**

*Last Updated: November 2024*
