import psycopg2
import psycopg2.errors
import json
import os
import sys
import uuid  # <-- ADDED: Required for the stateless demo route
from flask import Flask, jsonify, request, session, g
from flask_bcrypt import Bcrypt
from datetime import datetime
from flask_cors import CORS

# Local Imports
from config import Config

# Imports for geospatial logic (requires scripts folder to be on path or correctly imported)
# NOTE: Ensure you have an empty __init__.py in the 'scripts' folder.
try:
    # These imports rely on the functions being updated to match the expected signature
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


# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
# Initialize Flask-Bcrypt
bcrypt = Bcrypt(app)

# Global variables for DB connection
DB_CONN = None

# Define directories relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIFF_BASE_DIR = os.path.join(BASE_DIR)  # Assuming TIFFs are in the backend root
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DEMO_TEMP_DIR = os.path.join(
    STORAGE_DIR, "demo_temp"
)  # <-- ADDED: Temporary directory for demo uploads
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


@app.teardown_appcontext  # <-- ADDED: Explicitly handles connection closing
def close_db_connection(exception):
    """Closes the database connection at the end of the request context."""
    global DB_CONN
    if DB_CONN is not None and DB_CONN.closed == 0:
        try:
            DB_CONN.close()
            DB_CONN = None
        except Exception as e:
            print(f"Error closing DB connection in teardown: {e}")


# --- AUTHENTICATION ROUTES (Retained for completeness) ---


@app.route("/api/auth/signup", methods=["POST"])
def signup():
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
    # WARNING: THIS IS BLOCKING. Consider Celery/RQ for production.
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


@app.route("/api/aois", methods=["GET"])
def get_all_aois():
    """
    Retrieves a list of all AOIs for the authenticated user, including the BBOX as text.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = g.db
    cur = conn.cursor()

    try:
        # We use ST_AsText(bbox) to return the geometry as a human-readable WKT string
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
                "bbox_wkt": row[5],  # WKT string for visualization context
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
def get_latest_aoi_features(aoi_id):
    """
    Retrieves the road features (geometry) for the latest snapshot of a given AOI
    and returns it directly as a GeoJSON FeatureCollection.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = g.db
    cur = conn.cursor()

    try:
        # Step 1: Find the ID of the latest road_snapshot for this AOI
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

        # Step 2: Use PostGIS to aggregate all features from that snapshot into a single GeoJSON object
        # The query generates a GeoJSON feature for every row and aggregates them into a FeatureCollection.
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

        # The result is already a perfectly formatted GeoJSON dictionary (not a string)
        return jsonify(geojson_result), 200

    except Exception as e:
        print(f"Error fetching features for AOI {aoi_id}: {e}")
        return jsonify({"error": "Failed to retrieve road features."}), 500
    finally:
        cur.close()


@app.route("/api/aois/<int:aoi_id>", methods=["PUT"])
def update_aoi_metadata(aoi_id):
    """
    Updates the name and frequency of a specific AOI.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

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
def delete_aoi(aoi_id):
    """
    Deletes the AOI and all associated road snapshots and features via cascade delete,
    and removes the associated local GeoJSON files from the storage directory.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = g.db
    cur = conn.cursor()
    files_to_delete = []

    try:
        # 1. Get file paths BEFORE deleting the AOI (which cascades deletes DB records)
        cur.execute(
            "SELECT source_file FROM road_snapshots WHERE aoi_id = %s;", (aoi_id,)
        )
        files_to_delete = [row[0] for row in cur.fetchall()]

        # 2. Delete the AOI (ON DELETE CASCADE handles road_snapshots and road_features cleanup)
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

        # 3. Clean up local files
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


# ----------------------------------------------------------------------
# --- NEW ROUTES FOR SCHEDULING AND CHANGE DETECTION ---
# ----------------------------------------------------------------------


@app.route("/api/aois/<int:aoi_id>/process_new_snapshot", methods=["POST"])
def process_new_snapshot(aoi_id):
    """
    Simulates a scheduled run by fetching the AOI's image, processing it,
    and ingesting a new snapshot into the database.
    This route can be called by an internal scheduler (Celery, Cron, etc.).
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = g.db
    cur = conn.cursor()
    source_file_path = None

    try:
        # 1. Fetch AOI metadata (image name)
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

        # 2. RUN MODEL PROCESSOR (Reuse logic from AOI creation)
        geojson_data, _ = get_road_geojson(
            full_tiff_path
        )  # BBOX doesn't change, so ignore it

        # 3. Save the new GeoJSON Snapshot file
        os.makedirs(STORAGE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        geojson_filename = f"aoi_{aoi_id}_snap_{timestamp}.geojson"
        source_file_path = os.path.join(STORAGE_DIR, geojson_filename)

        with open(source_file_path, "w") as f:
            json.dump(geojson_data, f)

        # 4. Create new Snapshot Row
        cur.execute(
            """
            INSERT INTO road_snapshots (aoi_id, capture_date, source_file) 
            VALUES (%s, now(), %s) RETURNING id;
            """,
            (aoi_id, source_file_path),
        )
        snapshot_id = cur.fetchone()[0]
        print(f"[SCHEDULED] Created new road snapshot {snapshot_id}.")

        # 5. RUN INGEST SCRIPT (Populate features for the new snapshot)
        ingest_features_from_geojson(conn, source_file_path, snapshot_id)
        print(f"[SCHEDULED] Ingestion complete for snapshot {snapshot_id}.")

        # Note: AOI BBOX is NOT updated as it is assumed to be static.

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
            os.remove(source_file_path)  # Cleanup file if failure occurred after saving

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
def demo_change_detection():
    """
    Stateless route: Accepts two GeoJSON files, runs change detection locally,
    returns the changes, and cleans up temporary files immediately.
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
        # 1. Save files temporarily
        unique_id = uuid.uuid4().hex

        path_old = os.path.join(DEMO_TEMP_DIR, f"{unique_id}_old.geojson")
        path_new = os.path.join(DEMO_TEMP_DIR, f"{unique_id}_new.geojson")

        file_old.save(path_old)
        file_new.save(path_new)

        temp_files.extend([path_old, path_new])

        print(
            f"[DEMO] Running stateless change detection between {path_old} and {path_new}..."
        )

        # 2. RUN CHANGE DETECTION SCRIPT
        # The script accesses the database connection (g.db) for PostGIS operations
        change_geojson = detect_changes_stateless(path_old, path_new)

        print("[DEMO] Stateless detection complete.")

        # 3. Return result
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
        # 4. Clean up temporary files regardless of success/failure
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)


# ----------------------------------------------------------------------
# --- MAIN CHANGE DETECTION ROUTE ---
# ----------------------------------------------------------------------


@app.route("/api/aois/<int:aoi_id>/detect_changes", methods=["GET"])
def detect_aoi_changes(aoi_id):
    """
    Retrieves the two latest road snapshots for an AOI and runs change detection
    between the road_features linked to those two snapshots.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = g.db
    cur = conn.cursor()

    try:
        # 1. Get the two latest snapshot IDs for this AOI
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

        # 2. RUN DATABASE-BASED CHANGE DETECTION SCRIPT
        print(
            f"[DB CHANGE] Preparing to detect changes between Snapshots {snapshot_old_id} (Old) and {snapshot_new_id} (New)..."
        )

        # We now use the implemented function
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
