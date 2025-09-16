"""
change_detector.py
Usage:
    python change_detector.py <week1> <week2> [--snap SNAP_M] [--buffer BUFFER_M] [--threshold M] [--export-dir DIR]

Produces:
 - new_roads GeoJSON (MultiLineString, EPSG:4326)
 - removed_roads GeoJSON (MultiLineString, EPSG:4326)
 - lengths in meters
 - optionally write files to export-dir
"""

import psycopg2
import json
import argparse
import os
import sys

DB_HOST = "localhost"
DB_NAME = "road_db"
DB_USER = "akash"
DB_PASSWORD = "akash"


def fetch_union_3857(cur, week):
    """Return EWKT of the union geometry transformed to 3857 (meters)."""
    cur.execute(
        "SELECT ST_AsEWKT(ST_Transform(ST_Union(road_geom), 3857)) FROM road_networks WHERE week = %s;",
        (week,),
    )
    res = cur.fetchone()
    return res[0] if res and res[0] is not None else None


def detect_changes(conn, week1, week2, snap_tol_m=2.0, buffer_m=3.0, export_dir=None):
    """
    Logic:
      - Read unioned geom for each week and transform to 3857 (meters)
      - Snap each geometry to the other (tolerance snap_tol_m)
      - Buffer each by buffer_m meters to form corridors (polygons)
      - Difference (w2_buf - w1_buf) => new polygons
      - Difference (w1_buf - w2_buf) => removed polygons
      - Use ST_Boundary(...) to get lines for visualization & length calculation
      - Transform lines back to 4326 before ST_AsGeoJSON
    """
    cur = conn.cursor()

    w1_ewkt = fetch_union_3857(cur, week1)
    w2_ewkt = fetch_union_3857(cur, week2)

    if not w1_ewkt and not w2_ewkt:
        print("No data for either week. Aborting.")
        return None

    # If one week is empty, set a dummy empty geometry so SQL runs consistently
    if not w1_ewkt:
        w1_ewkt = "SRID=3857;MULTILINESTRING EMPTY"
    if not w2_ewkt:
        w2_ewkt = "SRID=3857;MULTILINESTRING EMPTY"

    sql = """
    WITH
      geom AS (
        SELECT
          ST_GeomFromEWKT(%s) AS w1,
          ST_GeomFromEWKT(%s) AS w2
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
          ST_Boundary(ST_Difference(w2_buf, w1_buf)) AS new_lines_m,
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
    new_geojson, new_len, removed_geojson, removed_len = row

    # convert to Python-friendly objects
    new_obj = json.loads(new_geojson) if new_geojson else None
    removed_obj = json.loads(removed_geojson) if removed_geojson else None

    total_len = float(new_len) + float(removed_len)

    result = {
        "new_roads": new_obj,
        "removed_roads": removed_obj,
        "new_length_m": round(float(new_len), 2),
        "removed_length_m": round(float(removed_len), 2),
        "total_change_m": round(total_len, 2),
    }

    # optional: export GeoJSON files
    if export_dir:
        os.makedirs(export_dir, exist_ok=True)
        if new_obj:
            with open(
                os.path.join(export_dir, f"new_roads_w{week1}_w{week2}.geojson"), "w"
            ) as f:
                json.dump(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {"type": "Feature", "geometry": new_obj, "properties": {}}
                        ],
                    },
                    f,
                )
        if removed_obj:
            with open(
                os.path.join(export_dir, f"removed_roads_w{week1}_w{week2}.geojson"),
                "w",
            ) as f:
                json.dump(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": removed_obj,
                                "properties": {},
                            }
                        ],
                    },
                    f,
                )

    cur.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("week1", type=int)
    parser.add_argument("week2", type=int)
    parser.add_argument(
        "--snap", type=float, default=2.0, help="snap tolerance in meters (default 2.0)"
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=3.0,
        help="buffer corridor in meters (default 3.0)",
    )
    parser.add_argument(
        "--threshold", type=float, default=50.0, help="alert threshold in meters"
    )
    parser.add_argument(
        "--export-dir", default=None, help="optional directory to write GeoJSON outputs"
    )
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

    out = detect_changes(
        conn,
        args.week1,
        args.week2,
        snap_tol_m=args.snap,
        buffer_m=args.buffer,
        export_dir=args.export_dir,
    )

    conn.close()

    if out is None:
        sys.exit(1)

    print(f"\nChanges detected between week {args.week1} and {args.week2}:")
    print(
        json.dumps(
            {"new_roads": out["new_roads"], "removed_roads": out["removed_roads"]},
            indent=2,
        )
    )

    print(f"\nNew roads length: {out['new_length_m']} meters")
    print(f"Removed roads length: {out['removed_length_m']} meters")
    print(f"Total change length: {out['total_change_m']} meters")

    if out["total_change_m"] > args.threshold:
        print(f"ALERT: Significant change detected (> {args.threshold} m)")
    else:
        print("Change below threshold. No alert.")
