"""
REST API Server pre Launchpad Dashboard - Production verzia
Umožňuje prepojenie s Wear OS hodinkami
Všetky citlivé údaje sa načítavajú z environment variables
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import hashlib
import os

from database import DatabaseManager
from config import SECRET_KEY

app = Flask(__name__)
CORS(app)  # Povolí requesty z iných zariadení

# Tajný kľúč pre JWT tokeny (načítaný z config.py - environment variable)
app.config['SECRET_KEY'] = SECRET_KEY

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
        'message': 'Launchpad Dashboard API v2.0',
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
    password_hash = hash_password(data['password'])
    
    # Overenie v databáze
    user = db.verify_user(username, password_hash)
    
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
    Zoznam úkonov pre daný sklad
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
    
    # Získaj user ID z username
    user = db.get_user_by_username(current_user['username'])
    if not user:
        return jsonify({'error': 'Používateľ nenájdený'}), 401
    
    user_id = user['id']  # ID z dictionary
    client_id = data['client_id']
    
    # Skontroluj či už má aktívny záznam
    active = db.get_active_time_record(user_id)
    if active:
        return jsonify({
            'error': 'Máš už spustený časovač',
            'record_id': active['record_id']
        }), 409
    
    # Vytvor nový záznam
    record_id = db.start_time_record(user_id, client_id)
    
    if record_id:
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Časovač spustený'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Nepodarilo sa spustiť časovač'
        }), 500

@app.route('/api/timer/stop', methods=['POST'])
@token_required
def stop_timer(current_user):
    """
    Zastavenie časovača s úkonom
    Body: {"record_id": 123, "task_id": 456}
    """
    data = request.get_json()
    
    if not data or not data.get('record_id'):
        return jsonify({'error': 'record_id je povinný'}), 400
    
    record_id = data['record_id']
    task_id = data.get('task_id')
    custom_task_name = data.get('custom_task_name')
    
    success = db.end_time_record(record_id, task_id, custom_task_name)
    
    if success:
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Časovač zastavený'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Nepodarilo sa zastaviť časovač'
        }), 500

@app.route('/api/timer/cancel', methods=['POST'])
@token_required
def cancel_timer(current_user):
    """
    Zrušenie (vymazanie) časovača
    Body: {"record_id": 123}
    """
    data = request.get_json()
    
    if not data or not data.get('record_id'):
        return jsonify({'error': 'record_id je povinný'}), 400
    
    record_id = data['record_id']
    
    success = db.cancel_time_record(record_id)
    
    if success:
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Časovač zrušený'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Nepodarilo sa zrušiť časovač'
        }), 500

@app.route('/api/timer/active', methods=['GET'])
@token_required
def get_active_timer(current_user):
    """
    Získanie aktívneho časovača
    Headers: Authorization: Bearer <token>
    """
    # Získaj user ID z username
    user = db.get_user_by_username(current_user['username'])
    if not user:
        return jsonify({'error': 'Používateľ nenájdený'}), 401
    
    user_id = user['id']  # ID z dictionary
    
    # Skontroluj aktívny záznam
    active = db.get_active_time_record(user_id)
    
    if active:
        return jsonify({
            'active': True,
            'record': {
                'record_id': active['record_id'],
                'client_name': active['client_name'],
                'start_time': active['start_time'].isoformat() if active['start_time'] else None,
                'elapsed_seconds': active['elapsed_seconds']
            }
        })
    else:
        return jsonify({
            'active': False,
            'record': None
        })

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """404 - Endpoint nenájdený"""
    return jsonify({'error': 'Endpoint nenájdený'}), 404

@app.errorhandler(500)
def server_error(error):
    """500 - Server error"""
    return jsonify({'error': 'Interná chyba servera'}), 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Development mode
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
