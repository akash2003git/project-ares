import psycopg2
import json
from flask import Flask, jsonify, request, session, g
from flask_bcrypt import Bcrypt
from config import Config
from utils.db_setup import FULL_SCHEMA_SQL
from datetime import datetime

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Bcrypt
bcrypt = Bcrypt(app)

# Global variables for DB connection
DB_CONN = None

# --- DATABASE CONNECTION UTILITIES ---


def get_db_connection():
    """Establishes and returns a new psycopg2 database connection."""
    global DB_CONN

    if DB_CONN is not None and DB_CONN.closed == 0:
        return DB_CONN

    try:
        DB_CONN = psycopg2.connect(
            host=app.config["DB_HOST"],
            database=app.config["DB_NAME"],
            user=app.config["DB_USER"],
            password=app.config["DB_PASSWORD"],
            port=app.config["DB_PORT"],
        )
        DB_CONN.set_session(autocommit=False)  # Important: Use transactions for safety!
        print("✅ Database connection established successfully.")
        return DB_CONN

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        DB_CONN = None
        return None


def get_current_user_id():
    """Retrieves the user ID from the session or returns None."""
    # In a real app, this would involve JWT or a proper session check.
    # For this MVP, we use the simple Flask session.
    return session.get("user_id")


# --- HOOKS ---


@app.before_request
def before_request():
    """Ensure database connection is available before each request."""
    g.db = get_db_connection()
    if g.db is None and request.path != "/":
        # For non-health check routes, fail fast if DB is down
        return jsonify({"error": "Database service unavailable."}), 503


@app.after_request
def after_request(response):
    """Closes the database connection if it exists and commits changes."""
    # We are setting autocommit=False in get_db_connection for safety.
    # If the request succeeds (no uncaught error), we commit.
    if hasattr(g, "db") and g.db:
        if response.status_code < 400:
            g.db.commit()
        # Note: Closing the connection for every request in a simple app
        # is often replaced by a connection pool in production, but this is safer for MVP.
        # However, since we are using a global DB_CONN, we don't close it here
        # to simplify the global connection pool concept. We rely on autocommit=False
        # and the manual commit/rollback logic.
    return response


# --- AUTHENTICATION ROUTES ---


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email and password are required."}), 400

    # 1. Hash the password
    try:
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    except Exception:
        return jsonify({"error": "Failed to hash password."}), 500

    conn = g.db
    cur = conn.cursor()
    user_id = None
    try:
        # 2. Insert user into database
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id;",
            (email, password_hash),
        )
        user_id = cur.fetchone()[0]
        # Commit handled by after_request

        # 3. Log user in immediately (optional, but convenient for signup)
        session["user_id"] = user_id

        return (
            jsonify(
                {
                    "message": "User created and logged in.",
                    "user_id": user_id,
                    "email": email,
                }
            ),
            201,
        )

    except psycopg2.errors.UniqueViolation:
        # Handle case where email already exists
        conn.rollback()
        return jsonify({"error": "This email is already registered."}), 409
    except Exception as e:
        conn.rollback()
        print(f"Signup error: {e}")
        return jsonify({"error": "An internal error occurred during signup."}), 500
    finally:
        cur.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email and password are required."}), 400

    conn = g.db
    cur = conn.cursor()

    try:
        # 1. Find user by email
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s;", (email,))
        user_record = cur.fetchone()

        if user_record is None:
            return jsonify({"error": "Invalid email or password."}), 401

        user_id, hashed_password = user_record

        # 2. Verify password
        if bcrypt.check_password_hash(hashed_password, password):
            # 3. Successful login: Set session
            session["user_id"] = user_id
            return (
                jsonify(
                    {"message": "Login successful.", "user_id": user_id, "email": email}
                ),
                200,
            )
        else:
            return jsonify({"error": "Invalid email or password."}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "An internal error occurred during login."}), 500
    finally:
        cur.close()


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Successfully logged out."}), 200


@app.route("/api/auth/me", methods=["GET"])
def me():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"message": "Not authenticated."}), 401

    conn = g.db
    cur = conn.cursor()

    try:
        cur.execute("SELECT email, created_at FROM users WHERE id = %s;", (user_id,))
        user_record = cur.fetchone()

        if user_record:
            email, created_at = user_record
            return (
                jsonify(
                    {
                        "user_id": user_id,
                        "email": email,
                        "created_at": created_at.isoformat(),
                    }
                ),
                200,
            )
        else:
            session.pop("user_id", None)  # Clear invalid session
            return jsonify({"message": "User not found."}), 404

    except Exception as e:
        print(f"Me error: {e}")
        return jsonify({"error": "An internal error occurred."}), 500
    finally:
        cur.close()


# --- HEALTH CHECK ROUTE (Kept for foundation test) ---


def test_db_connection_status():
    conn = get_db_connection()
    # ... (rest of the function is the same as before)
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True, "Connected to ares_mvp."
        except Exception as e:
            print(f"Database query failed: {e}")
            return False, f"Database connection failed during query test: {e}"
    else:
        return False, "Database connection failed during initialization."


@app.route("/", methods=["GET"])
def health_check():
    db_status, db_message = test_db_connection_status()

    response_data = {
        "status": "online",
        "service": "Project Ares Backend MVP",
        "database_status": db_status,
        "database_message": db_message,
        "timestamp": datetime.now().isoformat(),
    }

    if db_status:
        return jsonify(response_data), 200
    else:
        return jsonify(response_data), 503


# --- MAIN EXECUTION ---
if __name__ == "__main__":

    # Attempt connection when the app starts
    get_db_connection()

    # NOTE: Set a secure SECRET_KEY in config.py for session security!
    print("\n--- Project Ares Backend Ready ---")
    print(f"To run the application, use: flask run --debug\n")
