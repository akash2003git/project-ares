import psycopg2
import psycopg2.errors
import json
import os
import sys
from flask import Flask, jsonify, request, session, g
from flask_bcrypt import Bcrypt
from datetime import datetime

# Local Imports
from config import Config

# Imports for geospatial logic (requires scripts folder to be on path or correctly imported)
# NOTE: Ensure you have an empty __init__.py in the 'scripts' folder.
try:
    # These imports rely on the functions being updated to match the expected signature
    from scripts.model_processor import get_road_geojson
    from scripts.ingest_data import ingest_features_from_geojson
except ImportError as e:
    print(
        f"Error importing scripts: {e}. Check that scripts/model_processor.py and scripts/ingest_data.py exist."
    )
    sys.exit(1)


# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Bcrypt
bcrypt = Bcrypt(app)

# Global variables for DB connection
DB_CONN = None

# Define directories relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIFF_BASE_DIR = os.path.join(BASE_DIR)  # Assuming TIFFs are in the backend root
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
app.config["STORAGE_DIR"] = STORAGE_DIR  # Save this path in config


# --- DATABASE CONNECTION UTILITIES ---


def get_db_connection():
    """Establishes and returns a new psycopg2 database connection."""
    global DB_CONN

    # Reuse existing, open connection if available
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
        DB_CONN.set_session(autocommit=False)  # Critical for safe transactions
        print("✅ Database connection established successfully.")
        return DB_CONN

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        DB_CONN = None
        return None


def get_current_user_id():
    """Retrieves the user ID from the session or returns None."""
    # Uses Flask's client-side session cookie for user identification
    return session.get("user_id")


# --- HOOKS (Middleware) ---


@app.before_request
def before_request():
    """Ensure database connection is available and inject it into request context."""
    g.db = get_db_connection()
    if g.db is None and request.path != "/":
        # For non-health check routes, fail fast if DB is down
        return jsonify({"error": "Database service unavailable."}), 503


@app.after_request
def after_request(response):
    """Commits database changes on success or ensures rollback is ready."""
    if hasattr(g, "db") and g.db:
        if response.status_code < 400:
            # Commit changes only if the request was successful
            g.db.commit()
    return response


# --- AUTHENTICATION ROUTES (Omitted for brevity, but assumed to be here) ---


@app.route("/api/auth/signup", methods=["POST"])
# ... (your existing signup code)
def signup():
    # ... (omitted for file size, assume working)
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email and password are required."}), 400

    try:
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    except Exception:
        return jsonify({"error": "Failed to hash password."}), 500

    conn = g.db
    cur = conn.cursor()
    user_id = None
    try:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id;",
            (email, password_hash),
        )
        user_id = cur.fetchone()[0]
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
        conn.rollback()
        return jsonify({"error": "This email is already registered."}), 409
    except Exception as e:
        conn.rollback()
        print(f"Signup error: {e}")
        return jsonify({"error": "An internal error occurred during signup."}), 500
    finally:
        cur.close()


@app.route("/api/auth/login", methods=["POST"])
# ... (your existing login code)
def login():
    # ... (omitted for file size, assume working)
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email and password are required."}), 400

    conn = g.db
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s;", (email,))
        user_record = cur.fetchone()

        if user_record is None:
            return jsonify({"error": "Invalid email or password."}), 401

        user_id, hashed_password = user_record

        if bcrypt.check_password_hash(hashed_password, password):
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
            session.pop("user_id", None)
            return jsonify({"message": "User not found."}), 404

    except Exception as e:
        print(f"Me error: {e}")
        return jsonify({"error": "An internal error occurred."}), 500
    finally:
        cur.close()


# --- AOI ROUTES ---


@app.route("/api/aois", methods=["POST"])
def create_aoi_and_snapshot():
    # 1. Authentication Check
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json()
    name = data.get("name")
    image_name = data.get("image_name")  # e.g., 'test_image_1.tif'
    frequency = data.get("frequency", "Manual")  # Default to manual if not provided

    # 3. Validation
    if not all([name, image_name]):
        return jsonify({"error": "Missing required fields (name, image_name)."}), 400

    conn = g.db
    cur = conn.cursor()
    aoi_id = None
    source_file_path = None  # Define here for cleanup in the 'except' block

    # ----------------------------------------------------
    # START SYNCHRONOUS, LONG-RUNNING PROCESS (Transaction Begins)
    # All database operations are wrapped in this try/except block.
    # ----------------------------------------------------
    try:
        # 4. Insert AOI Row (The Parent Record)
        cur.execute(
            """
            INSERT INTO aois (user_id, name, image_name, frequency)
            VALUES (%s, %s, %s, %s) RETURNING id;
            """,
            (user_id, name, image_name, frequency),
        )
        aoi_id = cur.fetchone()[0]

        # 5. RUN MODEL PROCESSOR (BLOCKED: Model Inference + BBOX Calculation)
        full_tiff_path = os.path.join(TIFF_BASE_DIR, image_name)

        print(
            f"[PROCESS] Starting model processing for AOI {aoi_id} on {image_name}..."
        )

        # get_road_geojson returns (geojson_data_dict, bbox_wkt_string)
        # The script handles reading the TIFF, running the model, and calculating the BBOX
        geojson_data, bbox_wkt = get_road_geojson(full_tiff_path)

        if not bbox_wkt:
            # Check if processing failed to return any geometry
            raise ValueError(
                "Model processing failed to detect road features or calculate BBOX."
            )

        print(f"[PROCESS] Model complete. Calculated BBOX: {bbox_wkt}")

        # --- Temporary File Handling for GeoJSON ---
        # Save the GeoJSON output to disk for the road_snapshots source_file record.
        os.makedirs(STORAGE_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        geojson_filename = f"aoi_{aoi_id}_snap_{timestamp}.geojson"
        source_file_path = os.path.join(STORAGE_DIR, geojson_filename)

        with open(source_file_path, "w") as f:
            json.dump(geojson_data, f)

        # 6. Create Snapshot Row (Get the crucial 'snapshot_id')
        cur.execute(
            """
            INSERT INTO road_snapshots (aoi_id, capture_date, source_file) 
            VALUES (%s, now(), %s) RETURNING id;
            """,
            (aoi_id, source_file_path),
        )
        snapshot_id = cur.fetchone()[0]
        print(f"[PROCESS] Created road snapshot {snapshot_id}.")

        # 7. RUN MODIFIED INGEST SCRIPT (Populate Features)
        # This function performs feature insertion into 'road_features' using the active connection.
        ingest_features_from_geojson(conn, source_file_path, snapshot_id)
        print(f"[PROCESS] Ingestion complete for snapshot {snapshot_id}.")

        # 8. Update AOI with BBOX (Finalizes the AOI boundary)
        cur.execute(
            "UPDATE aois SET bbox = ST_SetSRID(ST_GeomFromEWKT(%s), 4326) WHERE id = %s;",
            (bbox_wkt, aoi_id),
        )
        # ----------------------------------------------------
        # END SYNCHRONOUS PROCESS
        # ----------------------------------------------------

        # Commit is handled by @app.after_request on successful return.

        return (
            jsonify(
                {
                    "message": "AOI created, processed, and ingested successfully.",
                    "aoi_id": aoi_id,
                    "snapshot_id": snapshot_id,
                    "processing_time": "Synchronous (Expected long-running time)",
                }
            ),
            201,
        )

    except FileNotFoundError as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        conn.rollback()  # CRITICAL: Rollback everything if any step failed
        print(f"AOI processing error: {e}")

        # Attempt to clean up the temporary GeoJSON file on failure
        if source_file_path and os.path.exists(source_file_path):
            os.remove(source_file_path)

        return (
            jsonify(
                {"error": f"An internal error occurred during AOI processing: {e}"}
            ),
            500,
        )
    finally:
        cur.close()


# --- HEALTH CHECK ROUTE ---


def test_db_connection_status():
    conn = get_db_connection()
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
    print("\n--- Project Ares Backend Ready ---")
    print(f"To run the application, use: flask run --debug\n")
