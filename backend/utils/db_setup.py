FULL_SCHEMA_SQL = """
-- PostgreSQL Commands to initialize the database schema
-- NOTE: The 'postgis' extension must be created manually:
-- psql -d ares_mvp -U akash -c "CREATE EXTENSION postgis;"

-- 1. users: Authentication and Authorization
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

-- 2. aois (Area of Interest): Parent container for road data
CREATE TABLE IF NOT EXISTS aois (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  image_name TEXT,                  -- Which TIFF was used
  frequency TEXT,                   -- weekly, monthly, etc.
  bbox GEOMETRY(POLYGON, 4326),     -- Bounding box for map preview
  created_at TIMESTAMP DEFAULT now()
);

-- 3. road_snapshots: Metadata for a single extraction run (The new 'week' ID)
CREATE TABLE IF NOT EXISTS road_snapshots (
  id SERIAL PRIMARY KEY,
  aoi_id INT NOT NULL REFERENCES aois(id) ON DELETE CASCADE,
  capture_date TIMESTAMP NOT NULL,
  source_file TEXT,                  -- GeoJSON/TIFF filename
  created_at TIMESTAMP DEFAULT now()
);

-- 4. road_features: The actual geospatial road geometries
CREATE TABLE IF NOT EXISTS road_features (
  id SERIAL PRIMARY KEY,
  snapshot_id INT NOT NULL REFERENCES road_snapshots(id) ON DELETE CASCADE,
  feature_type TEXT,
  road_geom GEOMETRY(MultiLineString, 4326),
  created_at TIMESTAMP DEFAULT now()
);
"""
