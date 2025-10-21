# Databázová konfigurácia - EXAMPLE
# Skopíruj tento súbor ako config.py a vyplň skutočné hodnoty
# ALEBO nastav environment variables (odporúčané pre produkciu)

import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'your_mysql_host'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'your_username'),
    'password': os.environ.get('DB_PASSWORD', 'your_password'),
    'database': os.environ.get('DB_NAME', 'your_database'),
    'charset': 'utf8mb4',
    'autocommit': True
}

# JWT Secret Key
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
