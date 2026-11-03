from sqlalchemy import text
from app.core.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version();")
        )
        print("PostgreSQL connection successful!")
        print(result.scalar())

except Exception as error:
    print("PostgreSQL connection failed:")
    print(error)

# if __name__ == "__main__":
# try:
#     test_database_connection()
# except Exception as error:
#     print(f"PostgreSQL connection failed: {error}")