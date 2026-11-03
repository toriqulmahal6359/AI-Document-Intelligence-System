import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


from sqlalchemy import text
from app.core.database import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.scalar_one()

        print("PostgreSQL connection successful!")
        print(version)


if __name__ == "__main__":
    try:
        test_database_connection()
    except Exception as error:
        print(f"PostgreSQL connection failed: {error}")
