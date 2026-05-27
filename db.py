import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_PG = bool(DATABASE_URL)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cases.db")
PH = '%s' if USE_PG else '?'


def _get_conn():
    if USE_PG:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _get_conn()
    c = conn.cursor()
    if USE_PG:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL,
                department TEXT NOT NULL,
                approval_summary TEXT NOT NULL,
                adopted_article TEXT NOT NULL,
                approval_line TEXT NOT NULL,
                embedding TEXT,
                is_custom INTEGER DEFAULT 0,
                deviation_reason TEXT DEFAULT '',
                consulted_with TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL,
                department TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS recent_queries (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                article TEXT NOT NULL
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL,
                department TEXT NOT NULL,
                approval_summary TEXT NOT NULL,
                adopted_article TEXT NOT NULL,
                approval_line TEXT NOT NULL,
                embedding TEXT,
                is_custom INTEGER DEFAULT 0,
                deviation_reason TEXT DEFAULT '',
                consulted_with TEXT DEFAULT ''
            )
        """)
        existing = {row[1] for row in c.execute("PRAGMA table_info(cases)").fetchall()}
        for col, definition in [
            ("is_custom", "INTEGER DEFAULT 0"),
            ("deviation_reason", "TEXT DEFAULT ''"),
            ("consulted_with", "TEXT DEFAULT ''"),
        ]:
            if col not in existing:
                c.execute(f"ALTER TABLE cases ADD COLUMN {col} {definition}")
        c.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL,
                department TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS recent_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                article TEXT NOT NULL
            )
        """)
    conn.commit()
    conn.close()


def save_case(user_name, department, approval_summary, adopted_article, approval_line,
              embedding=None, is_custom=0, deviation_reason="", consulted_with=""):
    conn = _get_conn()
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    emb_str = json.dumps(embedding) if embedding else None
    if USE_PG:
        c.execute("""
            INSERT INTO cases (timestamp, user_name, department, approval_summary, adopted_article,
                               approval_line, embedding, is_custom, deviation_reason, consulted_with)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (ts, user_name, department, approval_summary, adopted_article, approval_line,
              emb_str, is_custom, deviation_reason, consulted_with))
        case_id = c.fetchone()[0]
    else:
        c.execute("""
            INSERT INTO cases (timestamp, user_name, department, approval_summary, adopted_article,
                               approval_line, embedding, is_custom, deviation_reason, consulted_with)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, user_name, department, approval_summary, adopted_article, approval_line,
              emb_str, is_custom, deviation_reason, consulted_with))
        case_id = c.lastrowid
    conn.commit()
    conn.close()
    return case_id


def get_all_cases():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, timestamp, user_name, department, approval_summary, adopted_article,
               approval_line, embedding, is_custom, deviation_reason, consulted_with
        FROM cases ORDER BY timestamp DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def save_report(user_name, department, content):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO reports (timestamp, user_name, department, content) VALUES ({PH}, {PH}, {PH}, {PH})",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), user_name, department, content)
    )
    conn.commit()
    conn.close()


def get_all_reports():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id, timestamp, user_name, department, content, status FROM reports ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def update_report_status(report_id, status):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"UPDATE reports SET status = {PH} WHERE id = {PH}", (status, report_id))
    conn.commit()
    conn.close()


def update_case(case_id, approval_summary, adopted_article, approval_line,
                is_custom, deviation_reason, consulted_with):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"""
        UPDATE cases SET
            approval_summary = {PH},
            adopted_article = {PH},
            approval_line = {PH},
            is_custom = {PH},
            deviation_reason = {PH},
            consulted_with = {PH}
        WHERE id = {PH}
    """, (approval_summary, adopted_article, approval_line,
          is_custom, deviation_reason, consulted_with, case_id))
    conn.commit()
    conn.close()


def delete_case(case_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM cases WHERE id = {PH}", (case_id,))
    conn.commit()
    conn.close()


def delete_report(report_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM reports WHERE id = {PH}", (report_id,))
    conn.commit()
    conn.close()


def delete_all_reports():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM reports")
    conn.commit()
    conn.close()


def save_recent_query(article: str):
    if not article:
        return
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"INSERT INTO recent_queries (timestamp, article) VALUES ({PH}, {PH})",
              (datetime.now().strftime("%Y-%m-%d %H:%M"), article))
    c.execute("""
        DELETE FROM recent_queries WHERE id NOT IN (
            SELECT id FROM recent_queries ORDER BY timestamp DESC LIMIT 10
        )
    """)
    conn.commit()
    conn.close()


def get_recent_queries(limit: int = 5):
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute(f"SELECT article, timestamp FROM recent_queries ORDER BY timestamp DESC LIMIT {PH}", (limit,))
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows
