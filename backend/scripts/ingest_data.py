import psycopg2
import json
import os
import psycopg2.extras
from datetime import datetime

# NOTE: This script is designed to be called by app.py and uses the
# connection object passed to it, rather than connecting globally.


def ingest_features_from_geojson(conn, geojson_path: str, snapshot_id: int):
    """
    Reads a GeoJSON file from disk and bulk inserts road features into the
    'road_features' table, linked to the given snapshot_id.

    Args:
        conn: The active psycopg2 database connection object (g.db).
        geojson_path: The path to the GeoJSON file to ingest.
        snapshot_id: The ID of the parent road_snapshot record.
    """
    print(
        f"--- Starting Ingestion for Snapshot ID: {snapshot_id} from {os.path.basename(geojson_path)} ---"
    )

    if not os.path.exists(geojson_path):
        raise FileNotFoundError(
            f"GeoJSON file not found for ingestion at {geojson_path}"
        )

    with open(geojson_path, "r") as f:
        geo = json.load(f)

    cur = conn.cursor()
    insert_count = 0
    try:
        # SQL template for insertion into our road_features table
        insert_sql = """
            INSERT INTO road_features (snapshot_id, feature_type, road_geom)
            VALUES (%s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
        """

        # NOTE: Since the model_processor returns a FeatureCollection with usually one
        # MultiLineString feature, we iterate over features to handle any valid GeoJSON.

        for feat in geo.get("features", []):
            geom = feat.get("geometry")
            if geom is None:
                continue

            # The GeoJSON dictionary is dumped back to a string for PostGIS ingestion
            geom_json = json.dumps(geom)

            # Use the geometry type as the feature_type
            feature_type = geom.get("type", "MultiLineString")

            cur.execute(insert_sql, (snapshot_id, feature_type, geom_json))
            insert_count += 1

        print(
            f"--- Successfully inserted {insert_count} road features for snapshot {snapshot_id}. ---"
        )

    except Exception as e:
        print(f"Ingestion Failed: {e}")
        # Re-raise the exception. The rollback will be handled by the @app.after_request
        # logic or the main route's exception handler in app.py.
        raise
    finally:
        cur.close()


if __name__ == "__main__":
    print("Ingestion script is not designed to be run standalone.")
