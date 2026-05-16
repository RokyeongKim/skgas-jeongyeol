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
            embedding TEXT
        )
    """)
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
    conn.commit()
    conn.close()


def save_case(user_name, department, approval_summary, adopted_article, approval_line, embedding=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO cases (timestamp, user_name, department, approval_summary, adopted_article, approval_line, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        user_name, department, approval_summary, adopted_article, approval_line,
        json.dumps(embedding) if embedding else None
    ))
    conn.commit()
    conn.close()


def get_all_cases():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, timestamp, user_name, department, approval_summary, adopted_article, approval_line, embedding
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
