"""
Utility functions for password hashing and verification using Flask-Bcrypt.
"""

from flask_bcrypt import Bcrypt

# Bcrypt will be initialized in app.py


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    # We assume 'bcrypt' is initialized with the Flask app.
    # The actual hashing call needs the application instance.
    raise NotImplementedError("Bcrypt initialization must happen in app.py context.")


def check_password(hashed_password: str, password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    # The actual check needs the application instance.
    raise NotImplementedError("Bcrypt initialization must happen in app.py context.")
