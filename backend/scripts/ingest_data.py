"""
ingest_data.py
Usage:
    python ingest_data.py <geojson_file> <week> [--replace]

Ingests a GeoJSON FeatureCollection with LineString/MultiLineString features into PostGIS.
Optionally replace existing rows for the same week.
"""

import psycopg2
import json
import argparse
import os
from datetime import datetime

DB_HOST = "localhost"
DB_NAME = "road_db"
DB_USER = "akash"
DB_PASSWORD = "akash"


def ensure_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS road_networks (
            id SERIAL PRIMARY KEY,
            week INTEGER NOT NULL,
            feature_type TEXT,
            road_geom GEOMETRY(MultiLineString, 4326),
            created_at TIMESTAMP DEFAULT now()
        );
        """
    )
    conn.commit()
    cur.close()


def ingest(geojson_path, week, replace=False):
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(geojson_path)

    with open(geojson_path, "r") as f:
        geo = json.load(f)

    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        ensure_table(conn)
        cur = conn.cursor()

        if replace:
            cur.execute("DELETE FROM road_networks WHERE week = %s;", (week,))
            conn.commit()

        # insert each feature; convert geometry to MultiLineString on insert
        insert_sql = """
            INSERT INTO road_networks (week, feature_type, road_geom)
            VALUES (%s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
        """

        for feat in geo.get("features", []):
            geom = feat.get("geometry")
            if geom is None:
                continue
            geom_json = json.dumps(geom)
            feature_type = geom.get("type")
            cur.execute(insert_sql, (week, feature_type, geom_json))

        conn.commit()
        cur.close()
        print(f"Week {week} data ingested successfully from {geojson_path}.")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("geojson", help="Path to GeoJSON file (FeatureCollection)")
    parser.add_argument("week", type=int, help="Week id (integer)")
    parser.add_argument(
        "--replace", action="store_true", help="Replace existing week data"
    )
    args = parser.parse_args()

    ingest(args.geojson, args.week, replace=args.replace)
