import mysql.connector
from mysql.connector import Error
import hashlib
from config import DB_CONFIG

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Pripojenie k MySQL databáze"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("Úspešne pripojené k MySQL databáze")
        except Error as e:
            print(f"Chyba pri pripojení k databáze: {e}")
            self.connection = None
    
    def disconnect(self):
        """Odpojenie od databázy"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Odpojené od MySQL databázy")
    
    def ensure_connection(self):
        """Overí a obnoví pripojenie ak je potrebné"""
        try:
            if self.connection is None or not self.connection.is_connected():
                print("Pripojenie stratené, pokúšam sa znovu pripojiť...")
                self.connect()
            else:
                # Test pripojenia
                self.connection.ping(reconnect=True, attempts=3, delay=1)
        except Error as e:
            print(f"Chyba pri testovaní pripojenia: {e}")
            self.connect()
    
    def hash_password(self, password):
        """Hashovanie hesla pomocou SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username, password):
        """Overenie prihlasovacích údajov používateľa"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            password_hash = self.hash_password(password)
            
            query = """
            SELECT id, username, full_name, warehouse, role, is_active 
            FROM users 
            WHERE username = %s AND password_hash = %s AND is_active = TRUE
            """
            cursor.execute(query, (username, password_hash))
            user = cursor.fetchone()
            cursor.close()
            
            return user
        except Error as e:
            print(f"Chyba pri overovaní používateľa: {e}")
            return None
    
    def get_clients_by_warehouse(self, warehouse):
        """Získanie klientov podľa skladu"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT id, client_name 
            FROM clients 
            WHERE warehouse = %s AND is_active = TRUE
            ORDER BY client_name
            """
            cursor.execute(query, (warehouse,))
            clients = cursor.fetchall()
            cursor.close()
            
            return clients
        except Error as e:
            print(f"Chyba pri získavaní klientov: {e}")
            return []
    
    def add_client(self, client_name, warehouse, created_by):
        """Pridanie nového klienta"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO clients (client_name, warehouse, created_by)
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (client_name, warehouse, created_by))
            self.connection.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"Chyba pri pridávaní klienta: {e}")
            return False
    
    def remove_client(self, client_id, warehouse):
        """Odstránenie klienta (označenie ako neaktívny)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE clients 
            SET is_active = FALSE 
            WHERE id = %s AND warehouse = %s
            """
            cursor.execute(query, (client_id, warehouse))
            self.connection.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"Chyba pri odstraňovaní klienta: {e}")
            return False
    
    def start_time_record(self, user_id, client_id, description=""):
        """Začatie záznamu času"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO time_records (user_id, client_id, start_time, description)
            VALUES (%s, %s, NOW(), %s)
            """
            cursor.execute(query, (user_id, client_id, description))
            self.connection.commit()
            record_id = cursor.lastrowid
            cursor.close()
            
            return record_id
        except Error as e:
            print(f"Chyba pri začatí záznamu času: {e}")
            return None
    
    def end_time_record(self, record_id, task_id=None, custom_task_name=None):
        """Ukončenie záznamu času s voliteľným úkonom"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE time_records 
            SET end_time = NOW(), 
                duration_seconds = TIMESTAMPDIFF(SECOND, start_time, NOW()),
                task_id = %s,
                custom_task_name = %s
            WHERE id = %s AND end_time IS NULL
            """
            cursor.execute(query, (task_id, custom_task_name, record_id))
            self.connection.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"Chyba pri ukončení záznamu času: {e}")
            return False
    
    def cancel_time_record(self, record_id):
        """Zrušenie (zmazanie) aktívneho záznamu času"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            # Zmažeme len aktívne záznamy (tie ktoré nemajú end_time)
            query = "DELETE FROM time_records WHERE id = %s AND end_time IS NULL"
            cursor.execute(query, (record_id,))
            self.connection.commit()
            deleted_count = cursor.rowcount
            cursor.close()
            
            return deleted_count > 0
        except Error as e:
            print(f"Chyba pri zrušení záznamu času: {e}")
            return False
    
    def get_user_time_records(self, user_id, limit=50):
        """Získanie posledných záznamov času používateľa"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT tr.id, tr.start_time, tr.end_time, tr.duration_seconds,
                   tr.description, c.client_name
            FROM time_records tr
            JOIN clients c ON tr.client_id = c.id
            WHERE tr.user_id = %s
            ORDER BY tr.start_time DESC
            LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            records = cursor.fetchall()
            cursor.close()
            
            return records
        except Error as e:
            print(f"Chyba pri získavaní záznamov času: {e}")
            return []
    
    def get_warehouse_time_records(self, warehouse, start_date=None, end_date=None):
        """Získanie všetkých záznamov času pre konkrétny sklad"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Základný query s LEFT JOIN pre tasks
            query = """
            SELECT 
                tr.id,
                u.warehouse,
                u.username,
                u.full_name,
                c.client_name,
                t.task_name,
                tr.custom_task_name,
                tr.start_time,
                tr.end_time,
                tr.duration_seconds,
                tr.description
            FROM time_records tr
            JOIN users u ON tr.user_id = u.id
            JOIN clients c ON tr.client_id = c.id
            LEFT JOIN tasks t ON tr.task_id = t.id
            WHERE u.warehouse = %s
            """
            
            params = [warehouse]
            
            # Pridanie filtrov pre dátumy
            if start_date:
                query += " AND DATE(tr.start_time) >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND DATE(tr.start_time) <= %s"
                params.append(end_date)
            
            query += " ORDER BY tr.start_time DESC"
            
            cursor.execute(query, tuple(params))
            records = cursor.fetchall()
            cursor.close()
            
            return records
        except Error as e:
            print(f"Chyba pri získavaní záznamov skladu: {e}")
            return []
    
    def get_all_time_records(self, start_date=None, end_date=None):
        """Získanie všetkých záznamov času zo všetkých skladov"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            query = """
            SELECT 
                tr.id,
                u.warehouse,
                u.username,
                u.full_name,
                c.client_name,
                t.task_name,
                tr.custom_task_name,
                tr.start_time,
                tr.end_time,
                tr.duration_seconds,
                tr.description
            FROM time_records tr
            JOIN users u ON tr.user_id = u.id
            JOIN clients c ON tr.client_id = c.id
            LEFT JOIN tasks t ON tr.task_id = t.id
            WHERE 1=1
            """
            
            params = []
            
            if start_date:
                query += " AND DATE(tr.start_time) >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND DATE(tr.start_time) <= %s"
                params.append(end_date)
            
            query += " ORDER BY tr.start_time DESC"
            
            cursor.execute(query, tuple(params))
            records = cursor.fetchall()
            cursor.close()
            
            return records
        except Error as e:
            print(f"Chyba pri získavaní všetkých záznamov: {e}")
            return []
    
    def delete_time_record(self, record_id, warehouse):
        """Vymazanie jedného časového záznamu (len pre záznamy z daného skladu)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            DELETE tr FROM time_records tr
            JOIN users u ON tr.user_id = u.id
            WHERE tr.id = %s AND u.warehouse = %s
            """
            cursor.execute(query, (record_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri mazaní záznamu: {e}")
            return False
    
    def delete_multiple_time_records(self, record_ids, warehouse):
        """Vymazanie viacerých časových záznamov naraz"""
        self.ensure_connection()
        
        if not self.connection or not record_ids:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Vytvorenie placeholder-ov pre SQL query
            placeholders = ', '.join(['%s'] * len(record_ids))
            
            query = f"""
            DELETE tr FROM time_records tr
            JOIN users u ON tr.user_id = u.id
            WHERE tr.id IN ({placeholders}) AND u.warehouse = %s
            """
            
            # Pridanie warehouse na koniec parametrov
            params = list(record_ids) + [warehouse]
            
            cursor.execute(query, params)
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected
        except Error as e:
            print(f"Chyba pri mazaní viacerých záznamov: {e}")
            return False
    
    # ============================================
    # API METÓDY PRE WEAR OS
    # ============================================
    
    def verify_user(self, username, password_hash):
        """Overenie používateľa pre API (už hashované heslo)"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT id, username, full_name, warehouse, role, is_active 
            FROM users 
            WHERE username = %s AND password_hash = %s AND is_active = TRUE
            """
            cursor.execute(query, (username, password_hash))
            user = cursor.fetchone()
            cursor.close()
            
            return user
        except Error as e:
            print(f"Chyba pri overovaní používateľa: {e}")
            return None
    
    def get_clients(self, warehouse):
        """Získanie klientov pre API (tuple formát)"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT id, client_name, warehouse
            FROM clients 
            WHERE warehouse = %s AND is_active = TRUE
            ORDER BY client_name
            """
            cursor.execute(query, (warehouse,))
            clients = cursor.fetchall()
            cursor.close()
            
            return clients
        except Error as e:
            print(f"Chyba pri získavaní klientov: {e}")
            return []
    
    def get_user_by_username(self, username):
        """Získanie používateľa podľa username (tuple formát)"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT id, username, full_name, warehouse, role 
            FROM users 
            WHERE username = %s AND is_active = TRUE
            """
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()
            
            return user
        except Error as e:
            print(f"Chyba pri získavaní používateľa: {e}")
            return None
    
    def get_active_time_record(self, user_id):
        """Získanie aktívneho časového záznamu pre používateľa"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT 
                tr.id as record_id,
                c.client_name,
                tr.start_time,
                TIMESTAMPDIFF(SECOND, tr.start_time, NOW()) as elapsed_seconds
            FROM time_records tr
            JOIN clients c ON tr.client_id = c.id
            WHERE tr.user_id = %s AND tr.end_time IS NULL
            ORDER BY tr.start_time DESC
            LIMIT 1
            """
            cursor.execute(query, (user_id,))
            record = cursor.fetchone()
            cursor.close()
            
            return record
        except Error as e:
            print(f"Chyba pri získavaní aktívneho záznamu: {e}")
            return None
    
    # ============================================
    # SPRÁVA POUŽÍVATEĽOV (ADMIN)
    # ============================================
    
    def get_users_by_warehouse(self, warehouse):
        """Získanie všetkých používateľov z daného skladu"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT id, username, full_name, role, is_active, created_at
            FROM users 
            WHERE warehouse = %s
            ORDER BY created_at DESC
            """
            cursor.execute(query, (warehouse,))
            users = cursor.fetchall()
            cursor.close()
            
            return users
        except Error as e:
            print(f"Chyba pri získavaní používateľov: {e}")
            return []
    
    def add_user(self, username, password, full_name, warehouse, role='user'):
        """Pridanie nového používateľa"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            password_hash = self.hash_password(password)
            
            query = """
            INSERT INTO users (username, password_hash, full_name, warehouse, role)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (username, password_hash, full_name, warehouse, role))
            self.connection.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"Chyba pri pridávaní používateľa: {e}")
            return False
    
    def deactivate_user(self, user_id, warehouse):
        """Deaktivácia používateľa (len pre používateľov z daného skladu)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE users 
            SET is_active = FALSE 
            WHERE id = %s AND warehouse = %s AND role != 'admin'
            """
            cursor.execute(query, (user_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri deaktivácii používateľa: {e}")
            return False
    
    def activate_user(self, user_id, warehouse):
        """Aktivácia používateľa (len pre používateľov z daného skladu)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE users 
            SET is_active = TRUE 
            WHERE id = %s AND warehouse = %s
            """
            cursor.execute(query, (user_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri aktivácii používateľa: {e}")
            return False
    
    def change_user_password(self, user_id, new_password, warehouse):
        """Zmena hesla používateľa (len pre používateľov z daného skladu)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            password_hash = self.hash_password(new_password)
            
            query = """
            UPDATE users 
            SET password_hash = %s 
            WHERE id = %s AND warehouse = %s
            """
            cursor.execute(query, (password_hash, user_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri zmene hesla: {e}")
            return False
    
    def username_exists(self, username):
        """Kontrola či username už existuje"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = "SELECT COUNT(*) FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            count = cursor.fetchone()[0]
            cursor.close()
            
            return count > 0
        except Error as e:
            print(f"Chyba pri kontrole username: {e}")
            return False
    
    def delete_user(self, user_id, warehouse):
        """Úplné vymazanie používateľa (len pre používateľov z daného skladu, nie adminov)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            # Vymaže len non-admin používateľov z daného skladu
            query = """
            DELETE FROM users 
            WHERE id = %s AND warehouse = %s AND role != 'admin'
            """
            cursor.execute(query, (user_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri mazaní používateľa: {e}")
            return False
    
    # ============================================
    # SPRÁVA ÚKONOV (TASKS)
    # ============================================
    
    def get_tasks_by_warehouse(self, warehouse):
        """Získanie úkonov pre daný sklad"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT id, task_name, warehouse, is_predefined, created_at
            FROM tasks 
            WHERE warehouse = %s AND is_active = 1
            ORDER BY is_predefined DESC, task_name ASC
            """
            cursor.execute(query, (warehouse,))
            tasks = cursor.fetchall()
            cursor.close()
            
            return tasks
        except Error as e:
            print(f"Chyba pri získavaní úkonov: {e}")
            return []
    
    def get_tasks(self, warehouse):
        """Získanie úkonov pre API (tuple formát)"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT id, task_name, warehouse
            FROM tasks 
            WHERE warehouse = %s AND is_active = 1
            ORDER BY is_predefined DESC, task_name ASC
            """
            cursor.execute(query, (warehouse,))
            tasks = cursor.fetchall()
            cursor.close()
            
            return tasks
        except Error as e:
            print(f"Chyba pri získavaní úkonov: {e}")
            return []
    
    def add_task(self, task_name, warehouse, created_by):
        """Pridanie nového úkonu"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO tasks (task_name, warehouse, created_by, is_predefined)
            VALUES (%s, %s, %s, 0)
            """
            cursor.execute(query, (task_name, warehouse, created_by))
            self.connection.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"Chyba pri pridávaní úkonu: {e}")
            return False
    
    def remove_task(self, task_id, warehouse):
        """Odstránenie úkonu (len vlastné, nie predefinované)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE tasks 
            SET is_active = 0 
            WHERE id = %s AND warehouse = %s AND is_predefined = 0
            """
            cursor.execute(query, (task_id, warehouse))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            
            return affected > 0
        except Error as e:
            print(f"Chyba pri odstraňovaní úkonu: {e}")
            return False