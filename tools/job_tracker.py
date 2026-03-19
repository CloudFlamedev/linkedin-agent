import sqlite3
import hashlib

DB_PATH = "logs/applications.db"

def init_db():
    """Creates database and all tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT,
            job_title       TEXT,
            company         TEXT,
            job_url         TEXT,
            match_score     INTEGER,
            apply_method    TEXT,
            status          TEXT,
            feedback        TEXT,
            cover_letter    TEXT,
            missing_skills  TEXT,
            matched_skills  TEXT,
            job_hash        TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def get_job_hash(job_title: str, company: str) -> str:
    """Creates unique hash for each job."""
    unique = f"{job_title.lower().strip()}{company.lower().strip()}"
    return hashlib.md5(unique.encode()).hexdigest()

def is_already_processed(job_title: str, company: str) -> bool:
    """Returns True if this job was already processed before."""
    init_db()  # ensure table exists
    conn = sqlite3.connect(DB_PATH)
    job_hash = get_job_hash(job_title, company)
    cursor = conn.execute(
        "SELECT id FROM applications WHERE job_hash = ?",
        (job_hash,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_job_processed(job_title: str, company: str):
    """Inserts a minimal record so job won't be processed again."""
    init_db()  # ensure table exists
    conn = sqlite3.connect(DB_PATH)
    job_hash = get_job_hash(job_title, company)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO applications 
               (job_title, company, job_hash, timestamp)
               VALUES (?, ?, ?, datetime('now'))""",
            (job_title, company, job_hash)
        )
        conn.commit()
    except Exception as e:
        print(f"   ⚠️ Tracker error: {e}")
    finally:
        conn.close()