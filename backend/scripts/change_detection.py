import json
import psycopg2
import uuid
import os
from typing import Dict, Any

# This module houses the core logic for detecting changes between two geometric datasets
# (GeoJSON files for the demo, or database snapshots for AOI monitoring) using PostGIS.

# --- DATABASE FETCH HELPERS ---


def _get_ewkt_from_geojson(conn: psycopg2.connect, geojson_path: str) -> str:
    """
    Helper to load GeoJSON from a file, ingest it temporarily into PostGIS,
    union the geometry, and return the EWKT representation in SRID 3857.

    This technique is used for the stateless demo route to leverage the
    user's existing, complex PostGIS comparison logic (ST_Snap, ST_Buffer, etc.).
    """
    temp_table_name = f"temp_geom_{uuid.uuid4().hex}"
    cur = conn.cursor()

    try:
        # 1. Create a TEMPORARY table (dropped automatically at session end, but deleted manually below)
        cur.execute(
            f"""
            CREATE TEMPORARY TABLE {temp_table_name} (
                geom GEOMETRY(MultiLineString, 4326)
            ) ON COMMIT DROP; 
        """
        )

        # 2. Load and parse GeoJSON
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)

        features = geojson_data.get("features", [])

        # 3. Insert features into the temporary table
        for feature in features:
            geom = feature.get("geometry")
            if not geom or geom["type"] not in ["LineString", "MultiLineString"]:
                continue

            # PostGIS requires GeoJSON to match the declared type
            if geom["type"] == "LineString":
                geom_json = json.dumps(
                    {"type": "MultiLineString", "coordinates": [geom["coordinates"]]}
                )
            else:
                geom_json = json.dumps(geom)

            cur.execute(
                f"INSERT INTO {temp_table_name} (geom) VALUES (ST_GeomFromGeoJSON(%s));",
                (geom_json,),
            )

        # 4. Fetch the unioned geometry in 3857 EWKT
        cur.execute(
            f"""
            SELECT ST_AsEWKT(ST_Transform(ST_Union(geom), 3857)) 
            FROM {temp_table_name} 
            WHERE geom IS NOT NULL;
        """
        )

        ewkt = cur.fetchone()
        return ewkt[0] if ewkt and ewkt[0] is not None else None

    except Exception as e:
        conn.rollback()
        raise Exception(f"Error preparing GeoJSON for PostGIS comparison: {e}")
    finally:
        cur.close()


def _get_ewkt_from_snapshot(conn: psycopg2.connect, snapshot_id: int) -> str:
    """
    Fetches the unioned geometry of all road features belonging to a single snapshot,
    transformed to 3857 (meters) and returned as EWKT.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT ST_AsEWKT(ST_Transform(ST_Union(geom), 3857)) 
            FROM road_features 
            WHERE snapshot_id = %s;
            """,
            (snapshot_id,),
        )
        ewkt = cur.fetchone()
        return ewkt[0] if ewkt and ewkt[0] is not None else None
    finally:
        cur.close()


# --- CORE CHANGE DETECTION LOGIC ---


def _run_postgis_diff(
    conn: psycopg2.connect,
    w1_ewkt: str,
    w2_ewkt: str,
    snap_tol_m: float = 2.0,
    buffer_m: float = 3.0,
) -> Dict[str, Any]:
    """
    Runs the core PostGIS logic provided by the user, comparing two EWKT geometries.
    The result is a FeatureCollection GeoJSON ready for visualization.
    """
    cur = conn.cursor()

    # Handle cases where one or both geometries might be empty
    if not w1_ewkt and not w2_ewkt:
        return {
            "type": "FeatureCollection",
            "features": [],
            "metadata": {
                "new_length_m": 0.0,
                "removed_length_m": 0.0,
                "total_change_m": 0.0,
            },
        }

    # If one geometry is empty, use a dummy empty geometry so SQL runs consistently
    if not w1_ewkt:
        w1_ewkt = "SRID=3857;MULTILINESTRING EMPTY"
    if not w2_ewkt:
        w2_ewkt = "SRID=3857;MULTILINESTRING EMPTY"

    sql = """
    WITH
      geom AS (
        SELECT
          ST_GeomFromEWKT(%s) AS w1, -- Old GeoM (Snapshot 1)
          ST_GeomFromEWKT(%s) AS w2  -- New GeoM (Snapshot 2)
      ),
      snapped AS (
        SELECT
          ST_Snap(w1, w2, %s) AS w1_snap,
          ST_Snap(w2, w1, %s) AS w2_snap
        FROM geom
      ),
      buffered AS (
        SELECT
          ST_Buffer(w1_snap, %s) AS w1_buf,
          ST_Buffer(w2_snap, %s) AS w2_buf
        FROM snapped
      ),
      diffs AS (
        SELECT
          -- New Roads (W2 buffer MINUS W1 buffer) -> added/changed geometry
          ST_Boundary(ST_Difference(w2_buf, w1_buf)) AS new_lines_m,
          -- Removed Roads (W1 buffer MINUS W2 buffer) -> removed/changed geometry
          ST_Boundary(ST_Difference(w1_buf, w2_buf)) AS removed_lines_m
        FROM buffered
      )
    SELECT
      ST_AsGeoJSON(ST_Transform(new_lines_m, 4326)) AS new_geojson,
      COALESCE(ST_Length(new_lines_m), 0) AS new_len_m,
      ST_AsGeoJSON(ST_Transform(removed_lines_m, 4326)) AS removed_geojson,
      COALESCE(ST_Length(removed_lines_m), 0) AS removed_len_m
    FROM diffs;
    """

    cur.execute(sql, (w1_ewkt, w2_ewkt, snap_tol_m, snap_tol_m, buffer_m, buffer_m))
    row = cur.fetchone()
    cur.close()

    if not row:
        raise Exception("PostGIS core query failed to return results.")

    new_geojson, new_len, removed_geojson, removed_len = row

    # Convert to Python GeoJSON objects
    new_obj = json.loads(new_geojson) if new_geojson else None
    removed_obj = json.loads(removed_geojson) if removed_geojson else None

    # Standardize result structure to a FeatureCollection
    features = []
    new_len = float(new_len)
    removed_len = float(removed_len)

    # Added/New Roads
    if new_obj and new_obj.get("coordinates"):
        features.append(
            {
                "type": "Feature",
                "geometry": new_obj,
                "properties": {"change_type": "ADDED", "length_m": round(new_len, 2)},
            }
        )

    # Removed Roads
    if removed_obj and removed_obj.get("coordinates"):
        features.append(
            {
                "type": "Feature",
                "geometry": removed_obj,
                "properties": {
                    "change_type": "DELETED",
                    "length_m": round(removed_len, 2),
                },
            }
        )

    # Prepare final result dictionary
    result = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "new_length_m": round(new_len, 2),
            "removed_length_m": round(removed_len, 2),
            "total_change_m": round(new_len + removed_len, 2),
        },
    }

    return result


# --- PUBLIC FUNCTIONS FOR FLASK ROUTES ---


def detect_changes_stateless(path_old: str, path_new: str) -> Dict[str, Any]:
    """
    Stateless detection: Gets EWKT from two local GeoJSON files and runs the diff.
    """
    from flask import g

    conn = g.db

    if conn is None:
        raise ConnectionError(
            "Database connection not available for stateless change detection."
        )

    # 1. Get EWKT for the old GeoJSON
    w1_ewkt = _get_ewkt_from_geojson(conn, path_old)

    # 2. Get EWKT for the new GeoJSON
    w2_ewkt = _get_ewkt_from_geojson(conn, path_new)

    # 3. Run the core PostGIS diff
    return _run_postgis_diff(conn, w1_ewkt, w2_ewkt)


def detect_changes_database(
    conn: psycopg2.connect, snapshot_old_id: int, snapshot_new_id: int
) -> Dict[str, Any]:
    """
    Database detection: Gets EWKT from two stored road snapshots and runs the diff.
    """
    # 1. Get EWKT for the old snapshot
    w1_ewkt = _get_ewkt_from_snapshot(conn, snapshot_old_id)

    # 2. Get EWKT for the new snapshot
    w2_ewkt = _get_ewkt_from_snapshot(conn, snapshot_new_id)

    # 3. Run the core PostGIS diff
    return _run_postgis_diff(conn, w1_ewkt, w2_ewkt)
