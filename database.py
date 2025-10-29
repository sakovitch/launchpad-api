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
    
    def get_tasks(self, warehouse):
        """Získanie úkonov pre API (tuple formát)"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            
            # Skontroluj či existuje stĺpec display_order
            cursor.execute("SHOW COLUMNS FROM tasks LIKE 'display_order'")
            has_display_order = cursor.fetchone() is not None
            
            if has_display_order:
                query = """
                SELECT id, task_name, warehouse
                FROM tasks 
                WHERE warehouse = %s AND is_active = 1
                ORDER BY display_order ASC, task_name ASC
                """
            else:
                query = """
                SELECT id, task_name, warehouse
                FROM tasks 
                WHERE warehouse = %s AND is_active = 1
                ORDER BY task_name ASC
                """
            
            cursor.execute(query, (warehouse,))
            tasks = cursor.fetchall()
            cursor.close()
            
            return tasks
        except Error as e:
            print(f"Chyba pri získavaní úkonov: {e}")
            return []
    
    def get_user_by_username(self, username):
        """Získanie používateľa podľa username"""
        self.ensure_connection()
        
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
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
