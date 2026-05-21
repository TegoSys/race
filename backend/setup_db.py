import psycopg2
from core.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

def setup_database():
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                details TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                make VARCHAR(255) NOT NULL,
                model VARCHAR(255),
                chassis_id VARCHAR(100)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS races (
                id SERIAL PRIMARY KEY,
                race_name VARCHAR(255) NOT NULL,
                date DATE,
                track_id VARCHAR(100)
            );
        """)
        cur.execute("""
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
        """)
        cur.execute("""
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
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                analysis_type VARCHAR(100) NOT NULL,
                result_json JSONB
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rule_check_summaries (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES race_files(id) ON DELETE CASCADE,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_violations INTEGER,
                status VARCHAR(50),
                summary_json JSONB
            );
        """)
        cur.execute("""
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
        """)
    conn.close()
    print("Database setup completed successfully.")

if __name__ == "__main__":
    setup_database()
