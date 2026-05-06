from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

# Helper function to get database connection
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME']
    )

# --- SECURITY DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("Administrator access required.", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'student') # Default to student
        
        hashed_password = generate_password_hash(password)
        
        db = get_db_connection()
        cursor = db.cursor()
        
        try:
            cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
                           (fullname, email, hashed_password, role))
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash("Email already exists. Please use a different email.", "error")
        finally:
            cursor.close()
            db.close()
            
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['fullname'] = user['fullname']
            session['role'] = user['role']
            
            flash(f"Welcome back, {user['fullname']}!", "success")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid email or password.", "error")
            
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- STUDENT ROUTES ---
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    # Redirect admins if they accidentally end up here
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    return render_template('student/dashboard.html')

@app.route('/student/book')
@login_required
def book_slot():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    # Logic to fetch available slots will go here
    return render_template('student/book_slot.html')

# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/slots')
@login_required
@admin_required
def manage_slots():
    return render_template('admin/manage_slots.html')

@app.route('/admin/requests')
@login_required
@admin_required
def admin_requests():
    return render_template('admin/requests.html')

# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)