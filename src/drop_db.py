import duckdb
from pathlib import Path
from config import DB_FILE  # make sure DB_FILE points to "predictions.duckdb"

def delete_db():
    """Delete the DuckDB database file."""
    if DB_FILE.exists():
        DB_FILE.unlink()  # delete the file
        print(f"Database {DB_FILE} deleted successfully.")
    else:
        print(f"No database found at {DB_FILE}.")

if __name__ == "__main__":
    delete_db()
