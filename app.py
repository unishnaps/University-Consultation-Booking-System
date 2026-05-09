import os
from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

def get_db():
    """Open a new MySQL connection for the current request."""
    
    print("DB USER:", app.config['MYSQL_USER'])
    print("DB PASSWORD:", app.config['MYSQL_PASSWORD'])
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        port=app.config['MYSQL_PORT'],
        
    )


def query_db(sql, args=(), one=False, commit=False):
    """
    Execute *sql* with *args*.
    - If *commit* is True the change is written and the last-row id returned.
    - Otherwise a list of dicts (or a single dict if *one*) is returned.
    """
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, args)
        if commit:
            conn.commit()
            return cur.lastrowid
        result = cur.fetchone() if one else cur.fetchall()
        return result
    finally:
        cur.close()
        conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    """Landing / home page."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role_sel = request.form.get('role', 'student')

        user = query_db(
            'SELECT * FROM users WHERE email = %s AND role = %s',
            (email, role_sel), one=True
        )

        if user and check_password_hash(user['password_hash'], password):
            session['user_id']    = user['id']
            session['role']       = user['role']
            session['first_name'] = user['first_name']
            session['last_name']  = user['last_name']
            flash(f"Welcome back, {user['first_name']}!", 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))

        flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name  = request.form.get('first_name', '').strip()
        last_name   = request.form.get('last_name', '').strip()
        student_id  = request.form.get('student_id', '').strip()
        email       = request.form.get('email', '').strip()
        password    = request.form.get('password', '')
        confirm_pw  = request.form.get('confirm_password', '')

        # Basic validation
        if not all([first_name, last_name, student_id, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_pw:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')

        existing = query_db(
            'SELECT id FROM users WHERE email = %s OR student_id = %s',
            (email, student_id), one=True
        )
        if existing:
            flash('An account with this email or student ID already exists.', 'danger')
            return render_template('auth/register.html')

        pw_hash = generate_password_hash(password)
        query_db(
            '''INSERT INTO users (first_name, last_name, student_id, email, password_hash, role)
               VALUES (%s, %s, %s, %s, %s, 'student')''',
            (first_name, last_name, student_id, email, pw_hash),
            commit=True
        )
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    uid = session['user_id']

    upcoming = query_db(
        '''SELECT b.id, b.topic, b.status, b.notes,
                  s.date, s.start_time, s.end_time, s.slot_type
           FROM bookings b
           JOIN slots s ON b.slot_id = s.id
           WHERE b.student_id = %s AND b.status IN ('pending','approved')
             AND s.date >= CURDATE()
           ORDER BY s.date ASC, s.start_time ASC
           LIMIT 5''',
        (uid,)
    )

    stats = {
        'upcoming': len(upcoming),
        'total': query_db(
            'SELECT COUNT(*) AS c FROM bookings WHERE student_id = %s', (uid,), one=True
        )['c'],
        'unread_msgs': query_db(
            'SELECT COUNT(*) AS c FROM messages WHERE receiver_id = %s AND is_read = FALSE',
            (uid,), one=True
        )['c'],
    }

    quick_slots = query_db(
        '''SELECT id, date, start_time, end_time, slot_type
           FROM slots
           WHERE date >= CURDATE() AND booked_count < capacity
           ORDER BY date ASC, start_time ASC
           LIMIT 3'''
    )

    return render_template('student/dashboard.html',
                           upcoming=upcoming, stats=stats,
                           quick_slots=quick_slots)


@app.route('/student/slots')
@login_required
@student_required
def student_slots():
    slots = query_db(
        '''SELECT id, date, start_time, end_time, slot_type,
                  capacity, booked_count,
                  (capacity - booked_count) AS available
           FROM slots
           WHERE date >= CURDATE() AND booked_count < capacity
           ORDER BY date ASC, start_time ASC'''
    )
    return render_template('student/dashboard.html',
                           view='slots', slots=slots)


@app.route('/student/book', methods=['GET', 'POST'])
@login_required
@student_required
def book_slot():
    if request.method == 'POST':
        slot_id = request.form.get('slot_id')
        topic   = request.form.get('topic', '').strip()
        notes   = request.form.get('notes', '').strip()
        uid     = session['user_id']

        if not slot_id or not topic:
            flash('Please select a slot and enter a consultation topic.', 'danger')
        else:
            # Check slot still available
            slot = query_db(
                'SELECT * FROM slots WHERE id = %s AND booked_count < capacity',
                (slot_id,), one=True
            )
            if not slot:
                flash('This slot is no longer available.', 'danger')
            else:
                # Check student hasn't already booked this slot
                dupe = query_db(
                    '''SELECT id FROM bookings
                       WHERE student_id = %s AND slot_id = %s
                         AND status NOT IN ('rejected','cancelled')''',
                    (uid, slot_id), one=True
                )
                if dupe:
                    flash('You have already booked this slot.', 'warning')
                else:
                    query_db(
                        '''INSERT INTO bookings (student_id, slot_id, topic, notes)
                           VALUES (%s, %s, %s, %s)''',
                        (uid, slot_id, topic, notes), commit=True
                    )
                    # Increment booked count
                    query_db(
                        'UPDATE slots SET booked_count = booked_count + 1 WHERE id = %s',
                        (slot_id,), commit=True
                    )
                    flash('Booking request submitted! Awaiting admin approval.', 'success')
                    return redirect(url_for('my_bookings'))

    available_slots = query_db(
        '''SELECT id, date, start_time, end_time, slot_type
           FROM slots
           WHERE date >= CURDATE() AND booked_count < capacity
           ORDER BY date ASC, start_time ASC'''
    )
    return render_template('student/book_slot.html', slots=available_slots)

@app.route('/student/bookings')
@login_required
@student_required
def my_bookings():
    uid = session['user_id']
    bookings = query_db(
        '''SELECT b.id, b.topic, b.notes, b.status, b.submitted_at,
                  s.date, s.start_time, s.end_time, s.slot_type
           FROM bookings b
           JOIN slots s ON b.slot_id = s.id
           WHERE b.student_id = %s
           ORDER BY b.submitted_at DESC''',
        (uid,)
    )
    return render_template('student/dashboard.html',
                           view='bookings', bookings=bookings)


@app.route('/student/bookings/cancel/<int:booking_id>', methods=['POST'])
@login_required
@student_required
def cancel_booking(booking_id):
    uid = session['user_id']
    booking = query_db(
        'SELECT * FROM bookings WHERE id = %s AND student_id = %s',
        (booking_id, uid), one=True
    )
    if not booking:
        flash('Booking not found.', 'danger')
    elif booking['status'] == 'approved':
        flash('Cannot cancel an already-approved booking.', 'warning')
    else:
        query_db(
            "UPDATE bookings SET status = 'cancelled' WHERE id = %s",
            (booking_id,), commit=True
        )
        query_db(
            'UPDATE slots SET booked_count = booked_count - 1 WHERE id = %s',
            (booking['slot_id'],), commit=True
        )
        flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('my_bookings'))


@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_bookings = query_db(
        '''SELECT b.id, b.topic, b.status, b.submitted_at,
                  u.first_name, u.last_name, u.student_id AS sid,
                  s.date, s.start_time, s.end_time, s.slot_type
           FROM bookings b
           JOIN users u ON b.student_id = u.id
           JOIN slots s ON b.slot_id = s.id
           WHERE b.status = 'pending'
           ORDER BY b.submitted_at DESC
           LIMIT 10'''
    )

    today_slots = query_db(
        '''SELECT id, start_time, end_time, slot_type, capacity, booked_count
           FROM slots WHERE date = CURDATE()
           ORDER BY start_time ASC'''
    )

    summary = {
        'pending': query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE status='pending'", one=True)['c'],
        'approved': query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE status='approved'", one=True)['c'],
        'total_slots': query_db(
            'SELECT COUNT(*) AS c FROM slots', one=True)['c'],
        'total_students': query_db(
            "SELECT COUNT(*) AS c FROM users WHERE role='student'", one=True)['c'],
    }

    return render_template('admin/dashboard.html',
                           pending_bookings=pending_bookings,
                           today_slots=today_slots,
                           summary=summary)

@app.route('/admin/register_admin', methods=['POST'])
@login_required
@admin_required
def register_admin():
    first_name  = request.form.get('first_name', '').strip()
    last_name   = request.form.get('last_name', '').strip()
    email       = request.form.get('email', '').strip()
    password    = request.form.get('password', '')
    confirm_pw  = request.form.get('confirm_password', '')

    # Basic Validation
    if not all([first_name, last_name, email, password]):
        flash('All fields are required to register an admin.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if password != confirm_pw:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Check if user already exists
    existing = query_db('SELECT id FROM users WHERE email = %s', (email,), one=True)
    if existing:
        flash('An account with this email already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Hash password and insert as admin with NULL student_id
    pw_hash = generate_password_hash(password)
    query_db(
        '''INSERT INTO users (first_name, last_name, student_id, email, password_hash, role)
           VALUES (%s, %s, NULL, %s, %s, 'admin')''',
        (first_name, last_name, email, pw_hash),
        commit=True
    )
    
    flash(f'Admin {first_name} {last_name} registered successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/slots', methods=['GET'])
@login_required
@admin_required
def manage_slots():
    slots = query_db(
        '''SELECT id, date, start_time, end_time, slot_type, capacity, booked_count
           FROM slots
           ORDER BY date DESC, start_time ASC'''
    )
    return render_template('admin/manage_slots.html', slots=slots)


@app.route('/admin/slots/add', methods=['POST'])
@login_required
@admin_required
def add_slot():
    date       = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time   = request.form.get('end_time')
    slot_type  = request.form.get('slot_type', 'General Advising')
    capacity   = request.form.get('capacity', 1)

    if not all([date, start_time, end_time]):
        flash('Date, start time, and end time are required.', 'danger')
        return redirect(url_for('manage_slots'))

    query_db(
        '''INSERT INTO slots (date, start_time, end_time, slot_type, capacity, created_by)
           VALUES (%s, %s, %s, %s, %s, %s)''',
        (date, start_time, end_time, slot_type, capacity, session['user_id']),
        commit=True
    )
    flash('Consultation slot published successfully!', 'success')
    return redirect(url_for('manage_slots'))


@app.route('/admin/slots/delete/<int:slot_id>', methods=['POST'])
@login_required
@admin_required
def delete_slot(slot_id):
    query_db('DELETE FROM slots WHERE id = %s', (slot_id,), commit=True)
    flash('Slot deleted.', 'info')
    return redirect(url_for('manage_slots'))


@app.route('/admin/requests')
@login_required
@admin_required
def admin_requests():
    status_filter = request.args.get('status', 'all')
    if status_filter == 'all':
        bookings = query_db(
            '''SELECT b.id, b.topic, b.status, b.notes, b.submitted_at,
                      u.first_name, u.last_name, u.student_id AS sid,
                      s.date, s.start_time, s.end_time, s.slot_type
               FROM bookings b
               JOIN users u ON b.student_id = u.id
               JOIN slots s ON b.slot_id = s.id
               ORDER BY b.submitted_at DESC'''
        )
    else:
        bookings = query_db(
            '''SELECT b.id, b.topic, b.status, b.notes, b.submitted_at,
                      u.first_name, u.last_name, u.student_id AS sid,
                      s.date, s.start_time, s.end_time, s.slot_type
               FROM bookings b
               JOIN users u ON b.student_id = u.id
               JOIN slots s ON b.slot_id = s.id
               WHERE b.status = %s
               ORDER BY b.submitted_at DESC''',
            (status_filter,)
        )

    counts = {
        'pending': query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE status='pending'", one=True)['c'],
        'approved': query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE status='approved'", one=True)['c'],
        'rejected': query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE status='rejected'", one=True)['c'],
    }

    return render_template('admin/requests.html',
                           bookings=bookings, counts=counts,
                           current_filter=status_filter)


@app.route('/admin/requests/approve/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def approve_booking(booking_id):
    query_db(
        "UPDATE bookings SET status='approved' WHERE id=%s",
        (booking_id,), commit=True
    )
    flash('Booking approved.', 'success')
    return redirect(url_for('admin_requests'))


@app.route('/admin/requests/reject/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def reject_booking(booking_id):
    # Free up the slot capacity
    booking = query_db('SELECT slot_id FROM bookings WHERE id=%s', (booking_id,), one=True)
    if booking:
        query_db(
            'UPDATE slots SET booked_count = booked_count - 1 WHERE id=%s',
            (booking['slot_id'],), commit=True
        )
    query_db(
        "UPDATE bookings SET status='rejected' WHERE id=%s",
        (booking_id,), commit=True
    )
    flash('Booking rejected.', 'info')
    return redirect(url_for('admin_requests'))

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('index.html'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
