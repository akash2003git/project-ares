import psycopg2

DB_HOST = "localhost"
DB_NAME = "road_db"
DB_USER = "akash"  # Replace with your user
DB_PASSWORD = "akash"  # Replace with your password


def test_connection():
    """Connects to the PostgreSQL database and prints a success message."""
    conn = None
    try:
        # Connect to the database
        print("Connecting to the database...")
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        print("Connection successful!")

        # Create a cursor object to interact with the database
        cur = conn.cursor()

        # Execute a simple query to get the PostGIS version
        cur.execute("SELECT postgis_version();")
        version = cur.fetchone()[0]
        print(f"PostGIS version: {version}")

        # Close the cursor and connection
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to the database: {error}")

    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    test_connection()
