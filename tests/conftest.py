import os
import pytest
import asyncpg
from tortoise import Tortoise
from tortoise.exceptions import OperationalError

from app.config import settings

# Set test database URL
os.environ["DATABASE_URL"] = "postgres://test:test@localhost:5432/test_db"


@pytest.fixture(scope="session", autouse=True)
async def initialize_test_db():
	# Override settings for tests
	from app.config import settings
	settings.database_url = os.environ["DATABASE_URL"]

	# Create admin connection
	admin_conn = await asyncpg.connect("postgres://postgres@localhost/postgres")

	# Create test user
	await admin_conn.execute("""
        DO $$ 
        BEGIN
            CREATE USER test WITH PASSWORD 'test';
            ALTER USER test CREATEDB;
        EXCEPTION WHEN duplicate_object THEN 
            RAISE NOTICE 'User already exists';
        END $$;
    """)

	# Create test database
	await admin_conn.execute("DROP DATABASE IF EXISTS test_db")
	await admin_conn.execute("CREATE DATABASE test_db OWNER test")

	# Grant privileges
	await admin_conn.execute("GRANT ALL PRIVILEGES ON DATABASE test_db TO test")
	await admin_conn.close()

	# Initialize core DB
	await Tortoise.init(
		db_url=settings.database_url,
		modules={"models": ["app.models.core", "aerich.models"]},
	)
	await Tortoise.generate_schemas()
	yield

	# Cleanup: close all connections
	await Tortoise.close_connections()

	# Drop test database
	admin_conn = await asyncpg.connect("postgres://postgres@localhost/postgres")
	await admin_conn.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'test_db'
          AND pid <> pg_backend_pid()
    """)
	await admin_conn.execute("DROP DATABASE test_db")
	await admin_conn.close()


@pytest.fixture(autouse=True)
async def reset_db():
	"""Reset database state between tests"""
	# Get all tables
	conn = Tortoise.get_connection("default")
	tables = await conn.execute_query(
		"SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
	)

	# Truncate all tables
	for table in tables:
		await conn.execute_script(f"TRUNCATE TABLE {table['tablename']} CASCADE")

	# Reset sequences
	sequences = await conn.execute_query(
		"SELECT sequence_name FROM information_schema.sequences "
		"WHERE sequence_schema = 'public'"
	)
	for seq in sequences:
		await conn.execute_script(
			f"ALTER SEQUENCE {seq['sequence_name']} RESTART WITH 1"
		)