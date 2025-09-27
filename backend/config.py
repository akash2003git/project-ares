class Config:
    """Base configuration settings for the Flask application."""

    # --- PostgreSQL Database Configuration ---
    DB_HOST = "localhost"
    DB_NAME = "ares_mvp"
    DB_USER = "akash"
    DB_PASSWORD = "akash"
    DB_PORT = 5432

    # --- Flask Configuration ---
    SECRET_KEY = "my_super_secret_key"
    DEBUG = True

    # --- File Paths ---
    # Used for storing GeoJSON outputs from the model_processor
    STORAGE_DIR = "storage"
