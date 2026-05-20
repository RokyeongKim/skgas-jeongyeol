import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cases.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    # 기존 DB 마이그레이션 (컬럼 없을 경우에만 추가)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO cases (timestamp, user_name, department, approval_summary, adopted_article,
                           approval_line, embedding, is_custom, deviation_reason, consulted_with)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        user_name, department, approval_summary, adopted_article, approval_line,
        json.dumps(embedding) if embedding else None,
        is_custom, deviation_reason, consulted_with,
    ))
    conn.commit()
    conn.close()


def get_all_cases():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (timestamp, user_name, department, content)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), user_name, department, content))
    conn.commit()
    conn.close()


def get_all_reports():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, user_name, department, content, status FROM reports ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def update_report_status(report_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()


def update_case(case_id, approval_summary, adopted_article, approval_line,
                is_custom, deviation_reason, consulted_with):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE cases SET
            approval_summary = ?,
            adopted_article = ?,
            approval_line = ?,
            is_custom = ?,
            deviation_reason = ?,
            consulted_with = ?
        WHERE id = ?
    """, (approval_summary, adopted_article, approval_line,
          is_custom, deviation_reason, consulted_with, case_id))
    conn.commit()
    conn.close()


def delete_case(case_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()


def delete_report(report_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()


def delete_all_reports():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reports")
    conn.commit()
    conn.close()


def save_recent_query(article: str):
    if not article:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO recent_queries (timestamp, article) VALUES (?, ?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M"), article))
    c.execute("""
        DELETE FROM recent_queries WHERE id NOT IN (
            SELECT id FROM recent_queries ORDER BY timestamp DESC LIMIT 10
        )
    """)
    conn.commit()
    conn.close()


def get_recent_queries(limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT article, timestamp FROM recent_queries ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows
