# app.py  — SETU unified backend
import sqlite3, uuid, datetime, math, os, functools
from flask import (Flask, request, jsonify, session,
                   send_from_directory, redirect, url_for)
from flask_cors import CORS
import bcrypt

DB          = 'setu.db'
ADMIN_BOOTSTRAP_KEY = 'SETU2026'   # change this to anything secret
app         = Flask(__name__, static_folder='static')
app.secret_key = 'setu-secret-key-change-in-production'
CORS(app, supports_credentials=True)

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(q, args=(), one=False):
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(q, args)
    rv   = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def init_db():
    if not os.path.exists(DB):
        conn = get_conn()
        with open('schema.sql', 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print('✅ Database created from schema.sql')

# ─── Auth decorators ──────────────────────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'not_authenticated'}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'not_authenticated'}), 401
            if session.get('role') not in roles:
                return jsonify({'error': 'forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── Serve HTML pages ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('.', 'signup.html')

@app.route('/dashboard/first_responder')
def responder_dashboard():
    if session.get('role') != 'first_responder':
        return redirect('/')
    return send_from_directory('.', 'ambulance.html')

@app.route('/dashboard/hospital_staff')
def hospital_dashboard():
    if session.get('role') != 'hospital_staff':
        return redirect('/')
    return send_from_directory('.', 'hospital.html')

@app.route('/dashboard/patient')
def patient_dashboard():
    if session.get('role') != 'patient':
        return redirect('/')
    return send_from_directory('.', 'patient.html')

@app.route('/dashboard/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/')
    return send_from_directory('.', 'admin.html')

# ─── Auth API ─────────────────────────────────────────────────────────────────
@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Frontend calls this on load to restore session state."""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 200
    return jsonify({
        'authenticated': True,
        'user_id':   session['user_id'],
        'name':      session['name'],
        'role':      session['role'],
        'linked_id': session.get('linked_id'),
        'email':     session['email'],
    })

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data  = request.json
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')
    role  = data.get('role', '')

    if not email or not pwd or not role:
        return jsonify({'error': 'All fields required'}), 400

    user = query_db(
        'SELECT * FROM users WHERE email=? AND role=?', (email, role), one=True
    )
    if not user:
        return jsonify({'error': 'Invalid email or role'}), 401

    if not bcrypt.checkpw(pwd.encode(), user['password'].encode()):
        return jsonify({'error': 'Incorrect password'}), 401

    session['user_id']   = user['user_id']
    session['name']      = user['name']
    session['role']      = user['role']
    session['linked_id'] = user['linked_id']
    session['email']     = user['email']

    return jsonify({
        'message':   'Login successful',
        'role':      user['role'],
        'linked_id': user['linked_id'],
        'name':      user['name'],
    })

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/auth/signup/patient', methods=['POST'])
def signup_patient():
    """Patient self-signup — creates both users and patients records."""
    data = request.json

    # Required fields
    required = ['name','email','password','dob','gender','blood_group']
    for f in required:
        if not data.get(f, '').strip():
            return jsonify({'error': f'{f} is required'}), 400

    email = data['email'].strip().lower()
    if query_db('SELECT 1 FROM users WHERE email=?', (email,), one=True):
        return jsonify({'error': 'Email already registered'}), 409

    # Auto-generate patient_id (P001, P002 …)
    count      = query_db('SELECT COUNT(*) as c FROM patients', one=True)['c']
    patient_id = f'P{str(count + 1).zfill(3)}'

    user_id    = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    hashed     = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()

    query_db(
        'INSERT INTO users(user_id,name,email,password,role,linked_id,created_at) '
        'VALUES(?,?,?,?,?,?,?)',
        (user_id, data['name'], email, hashed, 'patient', patient_id, created_at)
    )
    query_db(
        'INSERT INTO patients(patient_id,name,dob,gender,blood_group,allergies,'
        'conditions,medications,biometric_template) VALUES(?,?,?,?,?,?,?,?,?)',
        (patient_id, data['name'], data['dob'], data['gender'], data['blood_group'],
         data.get('allergies','None'), data.get('conditions','None'),
         data.get('medications','None'),
         f'TEMPLATE-{str(count+1).zfill(3)}')
    )

    return jsonify({'message': 'Account created', 'patient_id': patient_id}), 201

@app.route('/auth/signup/admin', methods=['POST'])
def signup_admin():
    """One-time admin signup protected by bootstrap key."""
    data = request.json

    # Check bootstrap key
    if data.get('bootstrap_key','') != ADMIN_BOOTSTRAP_KEY:
        return jsonify({'error': 'Invalid bootstrap key'}), 403

    # Only one admin allowed
    if query_db("SELECT 1 FROM users WHERE role='admin'", one=True):
        return jsonify({'error': 'Admin already exists. Contact existing admin.'}), 409

    required = ['name','email','password']
    for f in required:
        if not data.get(f,'').strip():
            return jsonify({'error': f'{f} is required'}), 400

    email = data['email'].strip().lower()
    if query_db('SELECT 1 FROM users WHERE email=?', (email,), one=True):
        return jsonify({'error': 'Email already registered'}), 409

    user_id    = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    hashed     = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()

    query_db(
        'INSERT INTO users(user_id,name,email,password,role,linked_id,created_at) '
        'VALUES(?,?,?,?,?,?,?)',
        (user_id, data['name'], email, hashed, 'admin', None, created_at)
    )
    return jsonify({'message': 'Admin account created'}), 201

# ─── Admin API ────────────────────────────────────────────────────────────────
@app.route('/admin/create-user', methods=['POST'])
@role_required('admin')
def admin_create_user():
    """Admin creates hospital_staff or first_responder accounts."""
    data = request.json
    role = data.get('role','')

    if role not in ('hospital_staff', 'first_responder'):
        return jsonify({'error': 'Invalid role'}), 400

    required = ['name','email','password','linked_id']
    for f in required:
        if not data.get(f,'').strip():
            return jsonify({'error': f'{f} is required'}), 400

    email = data['email'].strip().lower()
    if query_db('SELECT 1 FROM users WHERE email=?', (email,), one=True):
        return jsonify({'error': 'Email already registered'}), 409

    # Validate linked_id exists
    linked_id = data['linked_id'].strip()
    if role == 'hospital_staff':
        if not query_db('SELECT 1 FROM hospitals WHERE hosp_id=?', (linked_id,), one=True):
            return jsonify({'error': 'Hospital not found'}), 404
    else:
        if not query_db('SELECT 1 FROM ambulances WHERE amb_id=?', (linked_id,), one=True):
            return jsonify({'error': 'Ambulance not found'}), 404

    user_id    = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    hashed     = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()

    query_db(
        'INSERT INTO users(user_id,name,email,password,role,linked_id,created_at) '
        'VALUES(?,?,?,?,?,?,?)',
        (user_id, data['name'], email, hashed, role, linked_id, created_at)
    )
    return jsonify({'message': f'{role} account created', 'user_id': user_id}), 201

@app.route('/admin/users', methods=['GET'])
@role_required('admin')
def admin_list_users():
    rows = query_db(
        "SELECT user_id,name,email,role,linked_id,created_at FROM users ORDER BY created_at DESC"
    )
    return jsonify([dict(r) for r in rows])

@app.route('/admin/check', methods=['GET'])
def admin_check():
    """Frontend uses this to know whether admin signup is still available."""
    exists = query_db("SELECT 1 FROM users WHERE role='admin'", one=True)
    return jsonify({'admin_exists': bool(exists)})

# ─── Patient API ──────────────────────────────────────────────────────────────
@app.route('/patient/profile', methods=['GET'])
@role_required('patient')
def patient_profile():
    pid = session['linked_id']
    p   = query_db('SELECT * FROM patients WHERE patient_id=?', (pid,), one=True)
    u   = query_db('SELECT name,email,created_at FROM users WHERE linked_id=?', (pid,), one=True)
    if not p:
        return jsonify({'error': 'not found'}), 404
    data = dict(p)
    if u:
        data['email']      = u['email']
        data['created_at'] = u['created_at']
    return jsonify(data)

@app.route('/patient/profile', methods=['PUT'])
@role_required('patient')
def update_patient_profile():
    pid  = session['linked_id']
    data = request.json
    query_db(
        'UPDATE patients SET name=?,dob=?,gender=?,blood_group=?,'
        'allergies=?,conditions=?,medications=? WHERE patient_id=?',
        (data.get('name'), data.get('dob'), data.get('gender'),
         data.get('blood_group'), data.get('allergies'),
         data.get('conditions'), data.get('medications'), pid)
    )
    # Also update name in users table
    query_db('UPDATE users SET name=? WHERE linked_id=?', (data.get('name'), pid))
    return jsonify({'message': 'Profile updated'})

# ─── Hospitals (public) ───────────────────────────────────────────────────────
@app.route('/hospitals', methods=['GET'])
def list_hospitals():
    rows = query_db('SELECT * FROM hospitals ORDER BY name')
    return jsonify([dict(r) for r in rows])

# ─── Patients (search — used by first responder) ──────────────────────────────
@app.route('/patients/<pid>', methods=['GET'])
def get_patient(pid):
    row = query_db('SELECT * FROM patients WHERE patient_id=?', (pid,), one=True)
    return (jsonify(dict(row)), 200) if row else (jsonify({'error':'not found'}), 404)

@app.route('/patients/search', methods=['GET'])
def search_patient():
    q = request.args.get('q','').strip()
    if not q:
        return jsonify([])
    pattern = f'%{q}%'
    rows = query_db(
        'SELECT patient_id,name,biometric_template FROM patients '
        'WHERE patient_id LIKE ? OR name LIKE ? OR biometric_template LIKE ? LIMIT 30',
        (pattern, pattern, pattern)
    )
    return jsonify([dict(r) for r in rows])

# ─── Ambulances ───────────────────────────────────────────────────────────────
@app.route('/ambulances_list', methods=['GET'])
@role_required('admin')
def list_ambulances():
    rows = query_db('SELECT * FROM ambulances ORDER BY amb_id')
    return jsonify([dict(r) for r in rows])

@app.route('/ambulances/<aid>', methods=['GET'])
def get_amb(aid):
    row = query_db('SELECT * FROM ambulances WHERE amb_id=?', (aid,), one=True)
    return (jsonify(dict(row)), 200) if row else (jsonify({'error':'not found'}), 404)

# ─── Ping / request logic ─────────────────────────────────────────────────────
def distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2)

def find_nearest_hospitals(amb_id, limit=3):
    amb = query_db('SELECT * FROM ambulances WHERE amb_id=?', (amb_id,), one=True)
    if not amb:
        return []
    rows = query_db("SELECT * FROM hospitals WHERE status='open'")
    ranked = sorted(
        [(distance(amb['current_lat'], amb['current_lng'], r['lat'], r['lng']), dict(r))
         for r in rows],
        key=lambda x: x[0]
    )
    return [h for _, h in ranked[:limit]]

@app.route('/ping', methods=['POST'])
@role_required('first_responder')
def ping():
    data              = request.json
    patient_id        = data.get('patient_id')
    urgency           = data.get('urgency', 'critical')
    current_situation = data.get('current_situation', '').strip()
    amb_id            = session['linked_id']     # always from session, never from client

    if not patient_id:
        return jsonify({'error': 'patient_id required'}), 400

    candidates = find_nearest_hospitals(amb_id, limit=3)
    batch_id   = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()

    for hosp in candidates:
        query_db(
            'INSERT INTO requests(req_id,batch_id,patient_id,amb_id,hosp_id,'
            'created_at,urgency,status,current_situation) VALUES(?,?,?,?,?,?,?,?,?)',
            (str(uuid.uuid4()), batch_id, patient_id, amb_id,
             hosp['hosp_id'], created_at, urgency, 'pending', current_situation)
        )

    return jsonify({
        'status':    'pings_sent',
        'batch_id':  batch_id,
        'hospitals': [h['name'] for h in candidates]
    })

@app.route('/pings/hospital/<hid>', methods=['GET'])
def pings_for_hospital(hid):
    rows = query_db("""
        SELECT r.*, p.name AS patient_name,
               p.dob, p.gender, p.blood_group,
               p.allergies, p.conditions, p.medications
        FROM requests r
        LEFT JOIN patients p ON r.patient_id = p.patient_id
        WHERE r.hosp_id=? AND r.status='pending'
        ORDER BY r.created_at
    """, (hid,))
    return jsonify([dict(r) for r in rows])

@app.route('/pings/<req_id>/respond', methods=['POST'])
@role_required('hospital_staff')
def respond(req_id):
    resp    = request.json.get('response')
    hosp_id = session['linked_id']    # always from session

    row = query_db('SELECT * FROM requests WHERE req_id=?', (req_id,), one=True)
    if not row:
        return jsonify({'error': 'not found'}), 404

    batch_id = row['batch_id']
    amb_id   = row['amb_id']

    if resp == 'accept':
        already = query_db(
            "SELECT * FROM requests WHERE batch_id=? AND status='assigned'",
            (batch_id,), one=True
        )
        if already:
            query_db(
                'UPDATE requests SET status=?,response_ts=? WHERE req_id=?',
                ('declined', datetime.datetime.utcnow().isoformat(), req_id)
            )
            return jsonify({'status': 'already_assigned'}), 200

        hosp = query_db('SELECT * FROM hospitals WHERE hosp_id=?', (hosp_id,), one=True)
        amb  = query_db('SELECT * FROM ambulances WHERE amb_id=?', (amb_id,), one=True)
        d    = distance(amb['current_lat'], amb['current_lng'], hosp['lat'], hosp['lng'])
        eta  = max(1, int(d * 100))

        query_db(
            'UPDATE requests SET status=?,assigned_hosp=?,response_ts=?,eta_minutes=? '
            'WHERE req_id=?',
            ('assigned', hosp_id, datetime.datetime.utcnow().isoformat(), eta, req_id)
        )
        query_db(
            'UPDATE requests SET status=? WHERE batch_id=? AND req_id<>?',
            ('closed', batch_id, req_id)
        )
        return jsonify({'status':'assigned','hospital_name':hosp['name'],'eta_minutes':eta})

    else:
        query_db(
            'UPDATE requests SET status=?,response_ts=? WHERE req_id=?',
            ('declined', datetime.datetime.utcnow().isoformat(), req_id)
        )
        return jsonify({'status': 'declined'})

@app.route('/amb/<amb_id>/pings', methods=['GET'])
@role_required('first_responder')
def amb_pings(amb_id):
    # Security: only allow querying your own ambulance
    if session['linked_id'] != amb_id:
        return jsonify({'error': 'forbidden'}), 403
    rows = query_db("""
        SELECT r.*, h.name AS hospital_name, p.name AS patient_name
        FROM requests r
        LEFT JOIN hospitals h ON r.hosp_id = h.hosp_id
        LEFT JOIN patients p ON r.patient_id = p.patient_id
        WHERE r.amb_id=?
        ORDER BY r.created_at DESC
    """, (amb_id,))
    return jsonify([dict(r) for r in rows])

@app.route('/logs', methods=['GET'])
@role_required('admin')
def logs():
    rows = query_db("""
        SELECT r.*, h.name AS hospital_name, p.name AS patient_name
        FROM requests r
        LEFT JOIN hospitals h ON r.hosp_id = h.hosp_id
        LEFT JOIN patients p ON r.patient_id = p.patient_id
        ORDER BY r.created_at DESC
    """)
    return jsonify([dict(r) for r in rows])

# ─── Boot ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(port=5000, debug=True)
