# config.py
import os

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "notasfiscais")

# Directory for storing uploaded and extracted files
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads") 