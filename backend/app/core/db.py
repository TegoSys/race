import psycopg2
from psycopg2.extras import RealDictCursor
from .config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
import logging

logger = logging.getLogger("race_agent")

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            cursor_factory=RealDictCursor
        )
        self.conn.autocommit = True

    def execute(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return None

    def execute_many(self, query, params_list):
        with self.conn.cursor() as cur:
            cur.executemany(query, params_list)

    def init_schema(self):
        """Initializes the database schema if tables do not exist."""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS drivers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                details TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                make VARCHAR(255) NOT NULL,
                model VARCHAR(255),
                chassis_id VARCHAR(100)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS races (
                id SERIAL PRIMARY KEY,
                race_name VARCHAR(255) NOT NULL,
                date DATE,
                track_id VARCHAR(100)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS race_files (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                driver_id INTEGER REFERENCES drivers(id),
                car_id INTEGER REFERENCES cars(id),
                race_id INTEGER REFERENCES races(id),
                metadata_json JSONB
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS channel_stats (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                channel_name VARCHAR(255) NOT NULL,
                unit VARCHAR(50),
                min_val FLOAT,
                max_val FLOAT,
                avg_val FLOAT,
                std_dev FLOAT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                analysis_type VARCHAR(100) NOT NULL,
                result_json JSONB
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS rule_check_summaries (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_violations INTEGER,
                status VARCHAR(50),
                summary_json JSONB
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS rule_violations (
                id SERIAL PRIMARY KEY,
                summary_id INTEGER REFERENCES rule_check_summaries(id) ON DELETE CASCADE,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                rule_id VARCHAR(100),
                severity VARCHAR(20),
                description TEXT,
                timestamp FLOAT,
                value FLOAT,
                context_json JSONB
            );
            """
        ]
        for table_sql in tables:
            self.execute(table_sql)

        # Migrations for existing tables
        try:
            self.execute("ALTER TABLE rule_violations ADD COLUMN IF NOT EXISTS summary_id INTEGER")
            self.execute("ALTER TABLE rule_violations ADD COLUMN IF NOT EXISTS description TEXT")
            self.execute("ALTER TABLE rule_violations ADD COLUMN IF NOT EXISTS context_json JSONB")
        except Exception as e:
            logger.warning(f"Migration failed for rule_violations: {e}")

db = Database()
