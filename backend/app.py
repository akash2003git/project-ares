from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import sys

# Add the 'scripts' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))

from change_detector import detect_changes

app = Flask(__name__)
CORS(app)

# Database config
DB_HOST = "localhost"
DB_NAME = "road_db"
DB_USER = "akash"
DB_PASSWORD = "akash"


@app.route("/", methods=["GET"])
def welcome():
    return jsonify({"message": "Welcome to ARES API!"})


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/api/detect_changes", methods=["GET"])
def get_changes():
    try:
        # Weeks from query parameters, default 1 and 2
        week1 = int(request.args.get("week1", 1))
        week2 = int(request.args.get("week2", 2))

        # Optional params
        snap = float(request.args.get("snap", 2.0))
        buffer = float(request.args.get("buffer", 3.0))
        threshold = float(request.args.get("threshold", 50.0))

        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )

        changes = detect_changes(conn, week1, week2, snap_tol_m=snap, buffer_m=buffer)

        conn.close()

        if changes:
            # Add threshold check here
            changes["alert"] = changes["total_change_m"] > threshold
            return jsonify(changes)
        else:
            return jsonify({"message": "No changes detected."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
