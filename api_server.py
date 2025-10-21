"""
REST API Server pre Launchpad Dashboard
Umožňuje prepojenie s Wear OS hodinkami
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import hashlib
from database import DatabaseManager
import os

app = Flask(__name__)
CORS(app)  # Povolí requesty z iných zariadení

# Tajný kľúč pre JWT tokeny
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')

db = DatabaseManager()

# ============================================
# HELPER FUNKCIE
# ============================================

def hash_password(password):
    """SHA256 hash hesla"""
    return hashlib.sha256(password.encode()).hexdigest()

def token_required(f):
    """Dekorátor pre overenie JWT tokenu"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token chýba'}), 401
        
        try:
            # Odstráň "Bearer " prefix ak existuje
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = {
                'username': data['username'],
                'warehouse': data['warehouse'],
                'role': data['role']
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expiroval'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Neplatný token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Kontrola či API beží"""
    return jsonify({
        'status': 'online',
        'message': 'Launchpad Dashboard API v1.0',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    """
    Prihlásenie používateľa
    Body: {"username": "...", "password": "..."}
    Returns: JWT token
    """
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username a password sú povinné'}), 400
    
    username = data['username']
    password = hash_password(data['password'])
    
    # Overenie v databáze
    user = db.verify_user(username, password)
    
    if not user:
        return jsonify({'error': 'Nesprávne prihlasovacie údaje'}), 401
    
    # Vytvorenie JWT tokenu (platnosť 30 dní)
    token = jwt.encode({
        'username': user['username'],
        'warehouse': user['warehouse'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        'token': token,
        'user': {
            'username': user['username'],
            'full_name': user['full_name'],
            'warehouse': user['warehouse'],
            'role': user['role']
        }
    })

@app.route('/api/clients', methods=['GET'])
@token_required
def get_clients(current_user):
    """
    Zoznam klientov pre daný sklad
    Headers: Authorization: Bearer <token>
    """
    warehouse = current_user['warehouse']
    clients = db.get_clients(warehouse)
    
    return jsonify({
        'clients': [
            {
                'id': client[0],
                'name': client[1],
                'warehouse': client[2]
            }
            for client in clients
        ]
    })

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    """
    Zoznam úkonov/actions pre daný sklad
    Headers: Authorization: Bearer <token>
    """
    warehouse = current_user['warehouse']
    tasks = db.get_tasks(warehouse)
    
    return jsonify({
        'tasks': [
            {
                'id': task[0],
                'name': task[1],
                'warehouse': task[2]
            }
            for task in tasks
        ]
    })

@app.route('/api/timer/start', methods=['POST'])
@token_required
def start_timer(current_user):
    """
    Spustenie časovača
    Body: {"client_id": 123}
    """
    data = request.get_json()
    
    if not data or not data.get('client_id'):
        return jsonify({'error': 'client_id je povinný'}), 400
    
    client_id = data['client_id']
    username = current_user['username']
    
    # Získaj user_id
    user = db.get_user_by_username(username)
    if not user:
        return jsonify({'error': 'Používateľ nenájdený'}), 404
    
    user_id = user[0]
    
    # Spusti časovač
    record_id = db.start_time_record(user_id, client_id)
    
    if record_id:
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Časovač spustený'
        })
    else:
        return jsonify({'error': 'Nepodarilo sa spustiť časovač'}), 500

@app.route('/api/timer/stop', methods=['POST'])
@token_required
def stop_timer(current_user):
    """
    Zastavenie časovača
    Body: {
        "record_id": 123,
        "task_id": 5,  // voliteľné - ID predefinovaného úkonu
        "custom_task_name": "My custom action"  // voliteľné - vlastný názov úkonu
    }
    """
    data = request.get_json()
    
    if not data or not data.get('record_id'):
        return jsonify({'error': 'record_id je povinný'}), 400
    
    record_id = data['record_id']
    task_id = data.get('task_id')  # môže byť None
    custom_task_name = data.get('custom_task_name')  # môže byť None
    
    # Zastav časovač s úkonom
    success = db.end_time_record(record_id, task_id, custom_task_name)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Časovač zastavený'
        })
    else:
        return jsonify({'error': 'Nepodarilo sa zastaviť časovač'}), 500

@app.route('/api/timer/cancel', methods=['POST'])
@token_required
def cancel_timer(current_user):
    """
    Zrušenie (zmazanie) aktívneho časovača
    Body: { record_id: int }
    """
    data = request.get_json()
    record_id = data.get('record_id')
    
    if not record_id:
        return jsonify({'error': 'record_id je povinný'}), 400
    
    # Zruš záznam (zmaž ho z databázy)
    success = db.cancel_time_record(record_id)
    
    if success:
        return jsonify({
            'message': 'Časovač zrušený',
            'cancelled': True
        })
    else:
        return jsonify({'error': 'Nepodarilo sa zrušiť časovač'}), 500

@app.route('/api/timer/active', methods=['GET'])
@token_required
def get_active_timer(current_user):
    """
    Získanie aktívneho časovača pre používateľa
    Returns: Aktívny záznam alebo null
    """
    username = current_user['username']
    
    # Získaj user_id
    user = db.get_user_by_username(username)
    if not user:
        return jsonify({'error': 'Používateľ nenájdený'}), 404
    
    user_id = user[0]
    
    # Nájdi aktívny záznam (kde end_time je NULL)
    active_record = db.get_active_time_record(user_id)
    
    if active_record:
        return jsonify({
            'active': True,
            'record': {
                'record_id': active_record['record_id'],
                'client_name': active_record['client_name'],
                'start_time': active_record['start_time'].isoformat(),
                'elapsed_seconds': active_record['elapsed_seconds']
            }
        })
    else:
        return jsonify({
            'active': False,
            'record': None
        })

@app.route('/api/timer/history', methods=['GET'])
@token_required
def get_timer_history(current_user):
    """
    História časových záznamov
    Query params: ?limit=10
    """
    username = current_user['username']
    warehouse = current_user['warehouse']
    limit = request.args.get('limit', 10, type=int)
    
    # Získaj posledných X záznamov
    records = db.get_user_time_records(username, warehouse, limit)
    
    return jsonify({
        'records': [
            {
                'record_id': rec['record_id'],
                'client_name': rec['client_name'],
                'start_time': rec['start_time'].isoformat() if rec['start_time'] else None,
                'end_time': rec['end_time'].isoformat() if rec['end_time'] else None,
                'duration_seconds': rec['duration_seconds']
            }
            for rec in records
        ]
    })

# ============================================
# SPUSTENIE SERVERA
# ============================================

if __name__ == '__main__':
    print("🚀 Launchpad Dashboard API Server")
    print("📡 Beží na http://localhost:5000")
    print("📱 Pripojené zariadenia môžu pristupovať na http://<tvoja-IP>:5000")
    print("\n💡 Pre prístup z hodiniek musíš byť na rovnakej WiFi sieti")
    print("=" * 60)
    
    # V produkcii použi host='0.0.0.0' pre prístup z iných zariadení
    app.run(host='0.0.0.0', port=5000, debug=True)
