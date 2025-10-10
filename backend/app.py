import psycopg2
import psycopg2.errors
import json
import os
import sys
import uuid
from flask import Flask, jsonify, request, session, g
from flask_bcrypt import Bcrypt
from datetime import datetime
from flask_cors import CORS
from functools import wraps

# Local Imports
# NOTE: config.py is required for app.config settings
from config import Config

# Imports for geospatial logic (requires scripts folder to be on path or correctly imported)
try:
    from scripts.model_processor import get_road_geojson
    from scripts.ingest_data import ingest_features_from_geojson
    from scripts.change_detection import (
        detect_changes_stateless,
        detect_changes_database,
    )
except ImportError as e:
    print(
        f"Error importing scripts: {e}. Check that scripts/model_processor.py and scripts/ingest_data.py exist."
    )
    sys.exit(1)


# --- INITIALIZATION & CONFIGURATION ---


app = Flask(__name__)
app.config.from_object(Config)

CORS(
    app,
    supports_credentials=True,
    resources={
        r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}
    },
)
bcrypt = Bcrypt(app)  # Initialize Flask-Bcrypt for password hashing

# Global variable for DB connection (managed by hooks/teardown)
DB_CONN = None

# Define directories relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIFF_BASE_DIR = os.path.join(BASE_DIR)
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DEMO_TEMP_DIR = os.path.join(STORAGE_DIR, "demo_temp")
app.config["STORAGE_DIR"] = STORAGE_DIR


# --- DECORATORS & UTILITIES ---


def get_current_user_id():
    """Retrieves the user ID from the Flask session or returns None."""
    # Uses Flask's client-side session cookie for user identification
    return session.get("user_id")


def login_required(f):
    """
    A custom decorator to check for a valid user session before running a route.
    If authenticated, it stores the user_id in Flask's global 'g' object.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if user_id is None:
            # Return 401 Unauthorized if the user is not logged in
            return jsonify({"error": "Authentication required."}), 401

        # Store user_id in the request global 'g' object for easy access in the route
        g.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function


# --- DATABASE CONNECTION UTILITIES ---


def get_db_connection():
    """Establishes and returns a new psycopg2 database connection."""

    # Check if a connection already exists in the request context (g object)
    if "db" in g and g.db is not None and g.db.closed == 0:
        return g.db  # Return the existing connection for the current request

    try:
        # Establish the new connection
        conn = psycopg2.connect(
            host=app.config["DB_HOST"],
            database=app.config["DB_NAME"],
            user=app.config["DB_USER"],
            password=app.config["DB_PASSWORD"],
            port=app.config["DB_PORT"],
        )
        conn.set_session(autocommit=False)
        print("✅ Database connection established successfully.")

        # Store it in g.db so it can be reused later in THIS request
        g.db = conn
        return conn

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        # Ensure g.db is None if connection fails
        g.db = None
        return None


# --- FLASK HOOKS (Middleware) ---


@app.before_request
def before_request():
    """
    Executed before every request. Ensures a database connection is established
    and accessible via g.db. Returns a 503 error if the DB is unavailable.
    """
    db_conn = get_db_connection()

    # Check g.db for the availability status
    if db_conn is None and request.path != "/":
        return jsonify({"error": "Database service unavailable."}), 503


@app.after_request
def after_request(response):
    """
    Executed after every request. Commits the transaction if the response was
    successful (status code < 400).
    """
    # Check if a connection was successfully opened and is not closed
    if "db" in g and g.db is not None and g.db.closed == 0:
        if response.status_code < 400:
            g.db.commit()
        else:
            g.db.rollback()

    return response


@app.teardown_appcontext
def close_db_connection(exception):
    """
    Executed after the request context is torn down. Closes the connection
    stored in g.db gracefully, if it exists.
    """
    if "db" in g and g.db is not None and g.db.closed == 0:
        try:
            g.db.close()
        except Exception as e:
            print(f"Error closing DB connection in teardown: {e}")


# --- AUTHENTICATION ROUTES (Public) ---


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    """Handles new user registration and logs them in immediately."""
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
def login():
    """Authenticates a user and sets the session cookie."""
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
    """Clears the user session cookie to log the user out."""
    session.pop("user_id", None)
    return jsonify({"message": "Successfully logged out."}), 200


@app.route("/api/auth/me", methods=["GET"])
@login_required
def me():
    """Retrieves the current authenticated user's details."""
    user_id = g.user_id

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


# --- AOI ROUTES (Protected) ---


@app.route("/api/aois", methods=["POST"])
@login_required
def create_aoi_and_snapshot():
    """
    Creates a new Area of Interest (AOI) and runs the initial road feature
    detection model, ingesting the first road snapshot. This is a synchronous,
    long-running process.
    """
    user_id = g.user_id
    data = request.get_json()
    name = data.get("name")
    image_name = data.get("image_name")
    frequency = data.get("frequency", "Manual")

    if not all([name, image_name]):
        return jsonify({"error": "Missing required fields (name, image_name)."}), 400

    conn = g.db
    cur = conn.cursor()
    aoi_id = None
    source_file_path = None

    try:
        # Insert AOI Row (The Parent Record)
        cur.execute(
            """
            INSERT INTO aois (user_id, name, image_name, frequency)
            VALUES (%s, %s, %s, %s) RETURNING id;
            """,
            (user_id, name, image_name, frequency),
        )
        aoi_id = cur.fetchone()[0]

        # RUN MODEL PROCESSOR (Model Inference + BBOX Calculation)
        full_tiff_path = os.path.join(TIFF_BASE_DIR, image_name)
        print(
            f"[PROCESS] Starting model processing for AOI {aoi_id} on {image_name}..."
        )

        geojson_data, bbox_wkt = get_road_geojson(full_tiff_path)

        if not bbox_wkt:
            raise ValueError(
                "Model processing failed to detect road features or calculate BBOX."
            )

        print(f"[PROCESS] Model complete. Calculated BBOX: {bbox_wkt}")

        # Save the GeoJSON output to disk
        os.makedirs(STORAGE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        geojson_filename = f"aoi_{aoi_id}_snap_{timestamp}.geojson"
        source_file_path = os.path.join(STORAGE_DIR, geojson_filename)

        with open(source_file_path, "w") as f:
            json.dump(geojson_data, f)

        # Create Snapshot Row
        cur.execute(
            """
            INSERT INTO road_snapshots (aoi_id, capture_date, source_file)
            VALUES (%s, now(), %s) RETURNING id;
            """,
            (aoi_id, source_file_path),
        )
        snapshot_id = cur.fetchone()[0]
        print(f"[PROCESS] Created road snapshot {snapshot_id}.")

        # RUN INGEST SCRIPT (Populate Features)
        ingest_features_from_geojson(conn, source_file_path, snapshot_id)
        print(f"[PROCESS] Ingestion complete for snapshot {snapshot_id}.")

        # Update AOI with BBOX (Finalizes the AOI boundary)
        cur.execute(
            "UPDATE aois SET bbox = ST_SetSRID(ST_GeomFromEWKT(%s), 4326) WHERE id = %s;",
            (bbox_wkt, aoi_id),
        )

        return (
            jsonify(
                {
                    "message": "AOI created, processed, and ingested successfully.",
                    "aoi_id": aoi_id,
                    "snapshot_id": snapshot_id,
                }
            ),
            201,
        )

    except FileNotFoundError as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        conn.rollback()  # Rollback everything if any step failed
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


@app.route("/api/aois", methods=["GET"])
@login_required
def get_all_aois():
    """Retrieves a list of all AOIs created by the authenticated user."""
    user_id = g.user_id

    conn = g.db
    cur = conn.cursor()

    try:
        # ST_AsText(bbox) converts the PostGIS geometry back to a WKT string
        cur.execute(
            """
            SELECT id, name, image_name, frequency, created_at, ST_AsText(bbox)
            FROM aois
            WHERE user_id = %s
            ORDER BY created_at DESC;
            """,
            (user_id,),
        )
        aois_data = cur.fetchall()

        aois_list = [
            {
                "id": row[0],
                "name": row[1],
                "image_name": row[2],
                "frequency": row[3],
                "created_at": row[4].isoformat(),
                "bbox_wkt": row[5],
            }
            for row in aois_data
        ]

        return jsonify(aois_list), 200

    except Exception as e:
        print(f"Error fetching AOIs: {e}")
        return jsonify({"error": "Failed to retrieve AOI list."}), 500
    finally:
        cur.close()


@app.route("/api/aois/<int:aoi_id>/latest_features", methods=["GET"])
@login_required
def get_latest_aoi_features(aoi_id):
    """
    Retrieves the road features (geometry) for the latest snapshot of a given AOI
    and returns it directly as a GeoJSON FeatureCollection.
    """
    user_id = g.user_id

    conn = g.db
    cur = conn.cursor()

    try:
        # Find the ID of the latest road_snapshot for this AOI
        cur.execute(
            """
            SELECT rs.id
            FROM road_snapshots rs
            JOIN aois a ON rs.aoi_id = a.id
            WHERE a.id = %s AND a.user_id = %s
            ORDER BY rs.capture_date DESC
            LIMIT 1;
            """,
            (aoi_id, user_id),
        )
        snapshot_id_record = cur.fetchone()

        if not snapshot_id_record:
            return jsonify({"error": "AOI not found or no snapshots exist."}), 404

        latest_snapshot_id = snapshot_id_record[0]

        # Use PostGIS to aggregate all features from that snapshot into a single GeoJSON object
        cur.execute(
            """
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', json_agg(ST_AsGeoJSON(rf.*)::json)
            )
            FROM road_features rf
            WHERE rf.snapshot_id = %s;
            """,
            (latest_snapshot_id,),
        )

        geojson_result = cur.fetchone()[0]
        return jsonify(geojson_result), 200

    except Exception as e:
        print(f"Error fetching features for AOI {aoi_id}: {e}")
        return jsonify({"error": "Failed to retrieve road features."}), 500
    finally:
        cur.close()


@app.route("/api/aois/<int:aoi_id>", methods=["PUT"])
@login_required
def update_aoi_metadata(aoi_id):
    """Updates the name and frequency of a specific AOI."""
    user_id = g.user_id

    data = request.get_json()
    name = data.get("name")
    frequency = data.get("frequency")

    if not name or not frequency:
        return (
            jsonify({"error": "Both 'name' and 'frequency' are required for update."}),
            400,
        )

    conn = g.db
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE aois
            SET name = %s, frequency = %s
            WHERE id = %s AND user_id = %s
            RETURNING id;
            """,
            (name, frequency, aoi_id, user_id),
        )

        if cur.rowcount == 0:
            return jsonify({"error": "AOI not found or unauthorized."}), 404

        return (
            jsonify(
                {"message": f"AOI ID {aoi_id} updated successfully.", "aoi_id": aoi_id}
            ),
            200,
        )

    except Exception as e:
        conn.rollback()
        print(f"Error updating AOI {aoi_id}: {e}")
        return jsonify({"error": "An internal error occurred during update."}), 500
    finally:
        cur.close()


@app.route("/api/aois/<int:aoi_id>", methods=["DELETE"])
@login_required
def delete_aoi(aoi_id):
    """
    Deletes the AOI, all associated database records (via CASCADE), and
    the corresponding local GeoJSON files from storage.
    """
    user_id = g.user_id

    conn = g.db
    cur = conn.cursor()
    files_to_delete = []

    try:
        # Get file paths BEFORE deleting the AOI
        cur.execute(
            "SELECT source_file FROM road_snapshots WHERE aoi_id = %s;", (aoi_id,)
        )
        files_to_delete = [row[0] for row in cur.fetchall()]

        # Delete the AOI
        cur.execute(
            """
            DELETE FROM aois
            WHERE id = %s AND user_id = %s
            RETURNING id;
            """,
            (aoi_id, user_id),
        )

        if cur.rowcount == 0:
            return jsonify({"error": "AOI not found or unauthorized."}), 404

        # Clean up local files
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[CLEANUP] Deleted file: {file_path}")

        return (
            jsonify(
                {
                    "message": f"AOI ID {aoi_id} and all related data deleted successfully, including local files.",
                    "aoi_id": aoi_id,
                }
            ),
            200,
        )

    except Exception as e:
        conn.rollback()
        print(f"Error deleting AOI {aoi_id}: {e}")
        return jsonify({"error": "An internal error occurred during deletion."}), 500
    finally:
        cur.close()


# --- NEW ROUTES FOR SCHEDULING AND CHANGE DETECTION ---


@app.route("/api/aois/<int:aoi_id>/process_new_snapshot", methods=["POST"])
@login_required
def process_new_snapshot(aoi_id):
    """
    Simulates a scheduled run by reprocessing the AOI's source image,
    ingesting a new snapshot into the database, but does NOT run change detection.
    """
    user_id = g.user_id

    conn = g.db
    cur = conn.cursor()
    source_file_path = None

    try:
        # Fetch AOI metadata (image name)
        cur.execute(
            "SELECT image_name FROM aois WHERE id = %s AND user_id = %s;",
            (aoi_id, user_id),
        )
        aoi_record = cur.fetchone()

        if not aoi_record:
            return jsonify({"error": "AOI not found or unauthorized."}), 404

        image_name = aoi_record[0]
        full_tiff_path = os.path.join(TIFF_BASE_DIR, image_name)

        print(f"[SCHEDULED] Starting re-processing for AOI {aoi_id} on {image_name}...")

        # RUN MODEL PROCESSOR (Reuse logic from AOI creation)
        geojson_data, _ = get_road_geojson(full_tiff_path)

        # Save the new GeoJSON Snapshot file
        os.makedirs(STORAGE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        geojson_filename = f"aoi_{aoi_id}_snap_{timestamp}.geojson"
        source_file_path = os.path.join(STORAGE_DIR, geojson_filename)

        with open(source_file_path, "w") as f:
            json.dump(geojson_data, f)

        # Create new Snapshot Row
        cur.execute(
            """
            INSERT INTO road_snapshots (aoi_id, capture_date, source_file)
            VALUES (%s, now(), %s) RETURNING id;
            """,
            (aoi_id, source_file_path),
        )
        snapshot_id = cur.fetchone()[0]
        print(f"[SCHEDULED] Created new road snapshot {snapshot_id}.")

        # RUN INGEST SCRIPT (Populate features for the new snapshot)
        ingest_features_from_geojson(conn, source_file_path, snapshot_id)
        print(f"[SCHEDULED] Ingestion complete for snapshot {snapshot_id}.")

        return (
            jsonify(
                {
                    "message": "New snapshot processed and ingested successfully.",
                    "aoi_id": aoi_id,
                    "new_snapshot_id": snapshot_id,
                }
            ),
            201,
        )

    except Exception as e:
        conn.rollback()
        print(f"Scheduled processing error for AOI {aoi_id}: {e}")

        if source_file_path and os.path.exists(source_file_path):
            os.remove(source_file_path)

        return (
            jsonify(
                {
                    "error": f"An internal error occurred during scheduled processing: {e}"
                }
            ),
            500,
        )
    finally:
        cur.close()


@app.route("/api/demo/change_detection", methods=["POST"])
# This is a public demo route for stateless operations, so it is NOT protected
def demo_change_detection():
    """
    Stateless route: Accepts two GeoJSON files (old and new), runs change
    detection locally using the database, returns the change GeoJSON, and cleans
    up temporary files immediately.
    """
    if "file_old" not in request.files or "file_new" not in request.files:
        return (
            jsonify({"error": "Missing 'file_old' and/or 'file_new' GeoJSON files."}),
            400,
        )

    file_old = request.files["file_old"]
    file_new = request.files["file_new"]

    if not file_old.filename.endswith(".geojson") or not file_new.filename.endswith(
        ".geojson"
    ):
        return (
            jsonify({"error": "Both uploaded files must be GeoJSON (.geojson)."}),
            400,
        )

    os.makedirs(DEMO_TEMP_DIR, exist_ok=True)
    temp_files = []

    try:
        # Save files temporarily
        unique_id = uuid.uuid4().hex

        path_old = os.path.join(DEMO_TEMP_DIR, f"{unique_id}_old.geojson")
        path_new = os.path.join(DEMO_TEMP_DIR, f"{unique_id}_new.geojson")

        file_old.save(path_old)
        file_new.save(path_new)

        temp_files.extend([path_old, path_new])

        print(
            f"[DEMO] Running stateless change detection between {path_old} and {path_new}..."
        )

        # RUN CHANGE DETECTION SCRIPT
        # The script uses the active database connection (g.db) for PostGIS operations
        change_geojson = detect_changes_stateless(path_old, path_new)  # Passed g.db

        print("[DEMO] Stateless detection complete.")

        # Return result
        return jsonify(change_geojson), 200

    except Exception as e:
        # Rollback temporary transaction in case of script failure
        if g.db:
            g.db.rollback()
        print(f"Stateless change detection error: {e}")
        return (
            jsonify({"error": f"An error occurred during change detection: {e}"}),
            500,
        )
    finally:
        # Clean up temporary files regardless of success/failure
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)


# --- MAIN CHANGE DETECTION ROUTE ---


@app.route("/api/aois/<int:aoi_id>/detect_changes", methods=["GET"])
@login_required
def detect_aoi_changes(aoi_id):
    """
    Retrieves the two latest road snapshots for an AOI and runs database-based
    change detection between them, returning the GeoJSON of the differences.
    """
    user_id = g.user_id

    conn = g.db
    cur = conn.cursor()

    try:
        # Get the two latest snapshot IDs for this AOI
        cur.execute(
            """
            SELECT rs.id
            FROM road_snapshots rs
            JOIN aois a ON rs.aoi_id = a.id
            WHERE a.id = %s AND a.user_id = %s
            ORDER BY rs.capture_date DESC
            LIMIT 2;
            """,
            (aoi_id, user_id),
        )
        snapshots = cur.fetchall()

        if len(snapshots) < 2:
            return (
                jsonify(
                    {
                        "error": "AOI requires at least two snapshots to perform change detection."
                    }
                ),
                404,
            )

        # snapshot_new is the most recent (index 0), snapshot_old is the second most recent (index 1)
        snapshot_new_id = snapshots[0][0]
        snapshot_old_id = snapshots[1][0]

        # RUN DATABASE-BASED CHANGE DETECTION SCRIPT
        print(
            f"[DB CHANGE] Detecting changes between Snapshots {snapshot_old_id} (Old) and {snapshot_new_id} (New)..."
        )

        change_geojson = detect_changes_database(conn, snapshot_old_id, snapshot_new_id)

        print(f"[DB CHANGE] Change detection successful.")

        return jsonify(change_geojson), 200

    except Exception as e:
        conn.rollback()
        print(f"Database change detection error for AOI {aoi_id}: {e}")
        return (
            jsonify(
                {"error": f"An error occurred during database change detection: {e}"}
            ),
            500,
        )
    finally:
        cur.close()


# --- HEALTH CHECK ROUTE (Public) ---


def test_db_connection_status():
    """Helper function to test the database connection and a simple query."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True, "Connected to ares_mvp and query successful."
        except Exception as e:
            print(f"Database query failed: {e}")
            return False, f"Database connection failed during query test: {e}"
    else:
        return False, "Database connection failed during initialization."


@app.route("/", methods=["GET"])
def health_check():
    """Provides a status check for the API service and database connection."""
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
    print("\n--- Project Ares Backend Ready ---")
    print(f"To run the application, use: flask run --debug\n")
