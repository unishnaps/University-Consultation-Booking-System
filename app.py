from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",      # Your MySQL username
    password="",      # Your MySQL password
    database="consultation_db"
)
cursor = db.cursor(dictionary=True)

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
                       (fullname, email, password, role))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Credentials"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'])

if __name__ == '__main__':
    app.run(debug=True)