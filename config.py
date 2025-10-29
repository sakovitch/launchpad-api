"""
Configuration for Launchpad API
Loads all sensitive data from environment variables for security
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists (local development)
load_dotenv()

# Database Configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'launchpad')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')

# Database connection config dictionary
DB_CONFIG = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'port': DB_PORT,
    'autocommit': False
}

# JWT Secret Key for token generation
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# API Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
