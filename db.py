import os
import json
import threading
from datetime import datetime

# ─── Backend selection ────────────────────────────────────────────────────────
DATABASE_URL  = os.environ.get('DATABASE_URL', '')
GITHUB_TOKEN  = os.environ.get('GITHUB_TOKEN', '')

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_PG     = bool(DATABASE_URL)
USE_GIST   = bool(GITHUB_TOKEN) and not USE_PG
USE_SQLITE = not USE_PG and not USE_GIST

DB_PATH = '/tmp/cases.db'
PH = '%s' if USE_PG else '?'

# ─── GitHub Gist backend ──────────────────────────────────────────────────────
if USE_GIST:
    import requests as _req

    _GIST_DESC = 'skgas-jeongyeol-db'
    _gist_id   = None
    _cache     = None
    _lock      = threading.Lock()

    def _gh_headers():
        return {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        }

    def _get_gist_id():
        global _gist_id
        if _gist_id:
            return _gist_id
        r = _req.get('https://api.github.com/gists', headers=_gh_headers(), timeout=15)
        for g in r.json():
            if g.get('description') == _GIST_DESC:
                _gist_id = g['id']
                return _gist_id
        # 처음 실행: 자동 생성
        initial = {'cases': [], 'reports': [], 'recent_queries': [],
                   'seq': {'cases': 0, 'reports': 0, 'recent_queries': 0}}
        r = _req.post('https://api.github.com/gists', headers=_gh_headers(), timeout=15, json={
            'description': _GIST_DESC,
            'public': False,
            'files': {'db.json': {'content': json.dumps(initial, ensure_ascii=False)}},
        })
        _gist_id = r.json()['id']
        return _gist_id

    def _load_gist():
        global _cache
        gid = _get_gist_id()
        r   = _req.get(f'https://api.github.com/gists/{gid}', headers=_gh_headers(), timeout=15)
        _cache = json.loads(r.json()['files']['db.json']['content'])
        # seq 필드 없으면 보정
        if 'seq' not in _cache:
            _cache['seq'] = {
                'cases':         max((c['id'] for c in _cache.get('cases', [])),         default=0),
                'reports':       max((c['id'] for c in _cache.get('reports', [])),       default=0),
                'recent_queries':max((c['id'] for c in _cache.get('recent_queries',[])), default=0),
            }

    def _flush():
        gid = _get_gist_id()
        _req.patch(f'https://api.github.com/gists/{gid}', headers=_gh_headers(), timeout=15, json={
            'files': {'db.json': {'content': json.dumps(_cache, ensure_ascii=False)}}
        })

    def _db():
        global _cache
        if _cache is None:
            _load_gist()
        return _cache

    def _next_id(table):
        d = _db()
        d['seq'][table] += 1
        return d['seq'][table]


# ─── SQLite / PostgreSQL helpers ──────────────────────────────────────────────
def _get_conn():
    if USE_PG:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


# ─── init_db ──────────────────────────────────────────────────────────────────
def init_db():
    if USE_GIST:
        _db()  # Gist 로드 (없으면 자동 생성)
        return

    conn = _get_conn()
    c = conn.cursor()
    if USE_PG:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL, user_name TEXT NOT NULL,
                department TEXT NOT NULL, approval_summary TEXT NOT NULL,
                adopted_article TEXT NOT NULL, approval_line TEXT NOT NULL,
                embedding TEXT, is_custom INTEGER DEFAULT 0,
                deviation_reason TEXT DEFAULT '', consulted_with TEXT DEFAULT ''
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY, timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL, department TEXT NOT NULL,
                content TEXT NOT NULL, status TEXT DEFAULT 'pending'
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS recent_queries (
                id SERIAL PRIMARY KEY, timestamp TEXT NOT NULL, article TEXT NOT NULL
            )""")
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, user_name TEXT NOT NULL,
                department TEXT NOT NULL, approval_summary TEXT NOT NULL,
                adopted_article TEXT NOT NULL, approval_line TEXT NOT NULL,
                embedding TEXT, is_custom INTEGER DEFAULT 0,
                deviation_reason TEXT DEFAULT '', consulted_with TEXT DEFAULT ''
            )""")
        existing = {row[1] for row in c.execute("PRAGMA table_info(cases)").fetchall()}
        for col, defn in [("is_custom","INTEGER DEFAULT 0"),
                          ("deviation_reason","TEXT DEFAULT ''"),
                          ("consulted_with","TEXT DEFAULT ''")]:
            if col not in existing:
                c.execute(f"ALTER TABLE cases ADD COLUMN {col} {defn}")
        c.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, user_name TEXT NOT NULL,
                department TEXT NOT NULL, content TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS recent_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, article TEXT NOT NULL
            )""")
    conn.commit()
    conn.close()


# ─── save_case ────────────────────────────────────────────────────────────────
def save_case(user_name, department, approval_summary, adopted_article, approval_line,
              embedding=None, is_custom=0, deviation_reason="", consulted_with=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if USE_GIST:
        with _lock:
            d = _db()
            cid = _next_id('cases')
            d['cases'].append({
                'id': cid, 'timestamp': ts,
                'user_name': user_name, 'department': department,
                'approval_summary': approval_summary,
                'adopted_article': adopted_article,
                'approval_line': approval_line,
                'is_custom': is_custom,
                'deviation_reason': deviation_reason,
                'consulted_with': consulted_with,
            })
            _flush()
        return cid

    conn = _get_conn()
    c = conn.cursor()
    emb_str = json.dumps(embedding) if embedding else None
    if USE_PG:
        c.execute("""
            INSERT INTO cases (timestamp,user_name,department,approval_summary,adopted_article,
                               approval_line,embedding,is_custom,deviation_reason,consulted_with)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (ts, user_name, department, approval_summary, adopted_article, approval_line,
              emb_str, is_custom, deviation_reason, consulted_with))
        cid = c.fetchone()[0]
    else:
        c.execute("""
            INSERT INTO cases (timestamp,user_name,department,approval_summary,adopted_article,
                               approval_line,embedding,is_custom,deviation_reason,consulted_with)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (ts, user_name, department, approval_summary, adopted_article, approval_line,
              emb_str, is_custom, deviation_reason, consulted_with))
        cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


# ─── get_all_cases ────────────────────────────────────────────────────────────
def get_all_cases():
    if USE_GIST:
        with _lock:
            rows = sorted(_db().get('cases', []), key=lambda x: x['timestamp'], reverse=True)
        return [(r['id'], r['timestamp'], r['user_name'], r['department'],
                 r['approval_summary'], r['adopted_article'], r['approval_line'],
                 None, r['is_custom'], r['deviation_reason'], r['consulted_with'])
                for r in rows]

    conn = _get_conn()
    c = conn.cursor()
    c.execute("""SELECT id,timestamp,user_name,department,approval_summary,adopted_article,
                        approval_line,embedding,is_custom,deviation_reason,consulted_with
                 FROM cases ORDER BY timestamp DESC""")
    rows = c.fetchall()
    conn.close()
    return rows


# ─── update_case ─────────────────────────────────────────────────────────────
def update_case(case_id, approval_summary, adopted_article, approval_line,
                is_custom, deviation_reason, consulted_with):
    if USE_GIST:
        with _lock:
            d = _db()
            for r in d['cases']:
                if r['id'] == case_id:
                    r['approval_summary']  = approval_summary
                    r['adopted_article']   = adopted_article
                    r['approval_line']     = approval_line
                    r['is_custom']         = is_custom
                    r['deviation_reason']  = deviation_reason
                    r['consulted_with']    = consulted_with
                    break
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"""UPDATE cases SET
        approval_summary={PH}, adopted_article={PH}, approval_line={PH},
        is_custom={PH}, deviation_reason={PH}, consulted_with={PH}
        WHERE id={PH}""",
        (approval_summary, adopted_article, approval_line,
         is_custom, deviation_reason, consulted_with, case_id))
    conn.commit()
    conn.close()


# ─── delete_case ─────────────────────────────────────────────────────────────
def delete_case(case_id):
    if USE_GIST:
        with _lock:
            d = _db()
            d['cases'] = [r for r in d['cases'] if r['id'] != case_id]
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM cases WHERE id={PH}", (case_id,))
    conn.commit()
    conn.close()


# ─── save_report ─────────────────────────────────────────────────────────────
def save_report(user_name, department, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if USE_GIST:
        with _lock:
            d = _db()
            rid = _next_id('reports')
            d['reports'].append({
                'id': rid, 'timestamp': ts,
                'user_name': user_name, 'department': department,
                'content': content, 'status': 'pending',
            })
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"INSERT INTO reports (timestamp,user_name,department,content) VALUES ({PH},{PH},{PH},{PH})",
              (ts, user_name, department, content))
    conn.commit()
    conn.close()


# ─── get_all_reports ─────────────────────────────────────────────────────────
def get_all_reports():
    if USE_GIST:
        with _lock:
            rows = sorted(_db().get('reports', []), key=lambda x: x['timestamp'], reverse=True)
        return [(r['id'], r['timestamp'], r['user_name'], r['department'],
                 r['content'], r['status']) for r in rows]

    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id,timestamp,user_name,department,content,status FROM reports ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows


# ─── delete_report ────────────────────────────────────────────────────────────
def delete_report(report_id):
    if USE_GIST:
        with _lock:
            d = _db()
            d['reports'] = [r for r in d['reports'] if r['id'] != report_id]
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM reports WHERE id={PH}", (report_id,))
    conn.commit()
    conn.close()


def delete_all_reports():
    if USE_GIST:
        with _lock:
            _db()['reports'] = []
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM reports")
    conn.commit()
    conn.close()


def update_report_status(report_id, status):
    if USE_GIST:
        with _lock:
            for r in _db().get('reports', []):
                if r['id'] == report_id:
                    r['status'] = status
                    break
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"UPDATE reports SET status={PH} WHERE id={PH}", (status, report_id))
    conn.commit()
    conn.close()


# ─── recent_queries ───────────────────────────────────────────────────────────
def save_recent_query(article: str):
    if not article:
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if USE_GIST:
        with _lock:
            d = _db()
            rid = _next_id('recent_queries')
            d['recent_queries'].append({'id': rid, 'timestamp': ts, 'article': article})
            d['recent_queries'] = sorted(d['recent_queries'],
                                         key=lambda x: x['timestamp'], reverse=True)[:10]
            _flush()
        return

    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"INSERT INTO recent_queries (timestamp,article) VALUES ({PH},{PH})", (ts, article))
    c.execute("""DELETE FROM recent_queries WHERE id NOT IN
                 (SELECT id FROM recent_queries ORDER BY timestamp DESC LIMIT 10)""")
    conn.commit()
    conn.close()


def get_recent_queries(limit: int = 5):
    if USE_GIST:
        with _lock:
            rows = sorted(_db().get('recent_queries', []),
                          key=lambda x: x['timestamp'], reverse=True)[:limit]
        return [(r['article'], r['timestamp']) for r in rows]

    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute(f"SELECT article,timestamp FROM recent_queries ORDER BY timestamp DESC LIMIT {PH}", (limit,))
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows
