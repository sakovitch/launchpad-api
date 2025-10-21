import mysql.connector
from mysql.connector import Error
import hashlib
import os

# Načítanie konfigurácie z environment variables
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', ''),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', ''),
    'charset': 'utf8mb4',
    'autocommit': True
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Pripojenie k MySQL databĂˇze"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("ĂšspeĹˇne pripojenĂ© k MySQL databĂˇze")
        except Error as e:
            print(f"Chyba pri pripojenĂ­ k databĂˇze: {e}")
            self.connection = None
    
    def disconnect(self):
        """Odpojenie od databĂˇzy"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("OdpojenĂ© od MySQL databĂˇzy")
    
    def ensure_connection(self):
        """OverĂ­ a obnovĂ­ pripojenie ak je potrebnĂ©"""
        try:
            if self.connection is None or not self.connection.is_connected():
                print("Pripojenie stratenĂ©, pokĂşĹˇam sa znovu pripojiĹĄ...")
                self.connect()
            else:
                # Test pripojenia
                self.connection.ping(reconnect=True, attempts=3, delay=1)
        except Error as e:
            print(f"Chyba pri testovanĂ­ pripojenia: {e}")
            self.connect()
    
    def hash_password(self, password):
        """Hashovanie hesla pomocou SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username, password):
        """Overenie prihlasovacĂ­ch Ăşdajov pouĹľĂ­vateÄľa"""
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
            print(f"Chyba pri overovanĂ­ pouĹľĂ­vateÄľa: {e}")
            return None
    
    def get_clients_by_warehouse(self, warehouse):
        """ZĂ­skanie klientov podÄľa skladu"""
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
            print(f"Chyba pri zĂ­skavanĂ­ klientov: {e}")
            return []
    
    def add_client(self, client_name, warehouse, created_by):
        """Pridanie novĂ©ho klienta"""
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
            print(f"Chyba pri pridĂˇvanĂ­ klienta: {e}")
            return False
    
    def remove_client(self, client_id, warehouse):
        """OdstrĂˇnenie klienta (oznaÄŤenie ako neaktĂ­vny)"""
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
            print(f"Chyba pri odstraĹovanĂ­ klienta: {e}")
            return False
    
    def start_time_record(self, user_id, client_id, description=""):
        """ZaÄŤatie zĂˇznamu ÄŤasu"""
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
            print(f"Chyba pri zaÄŤatĂ­ zĂˇznamu ÄŤasu: {e}")
            return None
    
    def end_time_record(self, record_id, task_id=None, custom_task_name=None):
        """UkonÄŤenie zĂˇznamu ÄŤasu s voliteÄľnĂ˝m Ăşkonom"""
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
            print(f"Chyba pri ukonÄŤenĂ­ zĂˇznamu ÄŤasu: {e}")
            return False
    
    def cancel_time_record(self, record_id):
        """ZruĹˇenie (zmazanie) aktĂ­vneho zĂˇznamu ÄŤasu"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            # ZmaĹľeme len aktĂ­vne zĂˇznamy (tie ktorĂ© nemajĂş end_time)
            query = "DELETE FROM time_records WHERE id = %s AND end_time IS NULL"
            cursor.execute(query, (record_id,))
            self.connection.commit()
            deleted_count = cursor.rowcount
            cursor.close()
            
            return deleted_count > 0
        except Error as e:
            print(f"Chyba pri zruĹˇenĂ­ zĂˇznamu ÄŤasu: {e}")
            return False
    
    def get_user_time_records(self, user_id, limit=50):
        """ZĂ­skanie poslednĂ˝ch zĂˇznamov ÄŤasu pouĹľĂ­vateÄľa"""
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
            print(f"Chyba pri zĂ­skavanĂ­ zĂˇznamov ÄŤasu: {e}")
            return []
    
    def get_warehouse_time_records(self, warehouse, start_date=None, end_date=None):
        """ZĂ­skanie vĹˇetkĂ˝ch zĂˇznamov ÄŤasu pre konkrĂ©tny sklad"""
        self.ensure_connection()
        
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # ZĂˇkladnĂ˝ query s LEFT JOIN pre tasks
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
            
            # Pridanie filtrov pre dĂˇtumy
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
            print(f"Chyba pri zĂ­skavanĂ­ zĂˇznamov skladu: {e}")
            return []
    
    def get_all_time_records(self, start_date=None, end_date=None):
        """ZĂ­skanie vĹˇetkĂ˝ch zĂˇznamov ÄŤasu zo vĹˇetkĂ˝ch skladov"""
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
            print(f"Chyba pri zĂ­skavanĂ­ vĹˇetkĂ˝ch zĂˇznamov: {e}")
            return []
    
    def delete_time_record(self, record_id, warehouse):
        """Vymazanie jednĂ©ho ÄŤasovĂ©ho zĂˇznamu (len pre zĂˇznamy z danĂ©ho skladu)"""
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
            print(f"Chyba pri mazanĂ­ zĂˇznamu: {e}")
            return False
    
    def delete_multiple_time_records(self, record_ids, warehouse):
        """Vymazanie viacerĂ˝ch ÄŤasovĂ˝ch zĂˇznamov naraz"""
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
            print(f"Chyba pri mazanĂ­ viacerĂ˝ch zĂˇznamov: {e}")
            return False
    
    # ============================================
    # API METĂ“DY PRE WEAR OS
    # ============================================
    
    def verify_user(self, username, password_hash):
        """Overenie pouĹľĂ­vateÄľa pre API (uĹľ hashovanĂ© heslo)"""
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
            print(f"Chyba pri overovanĂ­ pouĹľĂ­vateÄľa: {e}")
            return None
    
    def get_clients(self, warehouse):
        """ZĂ­skanie klientov pre API (tuple formĂˇt)"""
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
            print(f"Chyba pri zĂ­skavanĂ­ klientov: {e}")
            return []
    
    def get_user_by_username(self, username):
        """ZĂ­skanie pouĹľĂ­vateÄľa podÄľa username (tuple formĂˇt)"""
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
            print(f"Chyba pri zĂ­skavanĂ­ pouĹľĂ­vateÄľa: {e}")
            return None
    
    def get_active_time_record(self, user_id):
        """ZĂ­skanie aktĂ­vneho ÄŤasovĂ©ho zĂˇznamu pre pouĹľĂ­vateÄľa"""
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
            print(f"Chyba pri zĂ­skavanĂ­ aktĂ­vneho zĂˇznamu: {e}")
            return None
    
    # ============================================
    # SPRĂVA POUĹ˝ĂŤVATEÄ˝OV (ADMIN)
    # ============================================
    
    def get_users_by_warehouse(self, warehouse):
        """ZĂ­skanie vĹˇetkĂ˝ch pouĹľĂ­vateÄľov z danĂ©ho skladu"""
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
            print(f"Chyba pri zĂ­skavanĂ­ pouĹľĂ­vateÄľov: {e}")
            return []
    
    def add_user(self, username, password, full_name, warehouse, role='user'):
        """Pridanie novĂ©ho pouĹľĂ­vateÄľa"""
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
            print(f"Chyba pri pridĂˇvanĂ­ pouĹľĂ­vateÄľa: {e}")
            return False
    
    def deactivate_user(self, user_id, warehouse):
        """DeaktivĂˇcia pouĹľĂ­vateÄľa (len pre pouĹľĂ­vateÄľov z danĂ©ho skladu)"""
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
            print(f"Chyba pri deaktivĂˇcii pouĹľĂ­vateÄľa: {e}")
            return False
    
    def activate_user(self, user_id, warehouse):
        """AktivĂˇcia pouĹľĂ­vateÄľa (len pre pouĹľĂ­vateÄľov z danĂ©ho skladu)"""
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
            print(f"Chyba pri aktivĂˇcii pouĹľĂ­vateÄľa: {e}")
            return False
    
    def change_user_password(self, user_id, new_password, warehouse):
        """Zmena hesla pouĹľĂ­vateÄľa (len pre pouĹľĂ­vateÄľov z danĂ©ho skladu)"""
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
        """Kontrola ÄŤi username uĹľ existuje"""
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
        """ĂšplnĂ© vymazanie pouĹľĂ­vateÄľa (len pre pouĹľĂ­vateÄľov z danĂ©ho skladu, nie adminov)"""
        self.ensure_connection()
        
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            # VymaĹľe len non-admin pouĹľĂ­vateÄľov z danĂ©ho skladu
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
            print(f"Chyba pri mazanĂ­ pouĹľĂ­vateÄľa: {e}")
            return False
    
    # ============================================
    # SPRĂVA ĂšKONOV (TASKS)
    # ============================================
    
    def get_tasks_by_warehouse(self, warehouse):
        """ZĂ­skanie Ăşkonov pre danĂ˝ sklad"""
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
            print(f"Chyba pri zĂ­skavanĂ­ Ăşkonov: {e}")
            return []
    
    def get_tasks(self, warehouse):
        """ZĂ­skanie Ăşkonov pre API (tuple formĂˇt)"""
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
            print(f"Chyba pri zĂ­skavanĂ­ Ăşkonov: {e}")
            return []
    
    def add_task(self, task_name, warehouse, created_by):
        """Pridanie novĂ©ho Ăşkonu"""
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
            print(f"Chyba pri pridĂˇvanĂ­ Ăşkonu: {e}")
            return False
    
    def remove_task(self, task_id, warehouse):
        """OdstrĂˇnenie Ăşkonu (len vlastnĂ©, nie predefinovanĂ©)"""
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
            print(f"Chyba pri odstraĹovanĂ­ Ăşkonu: {e}")
            return False
