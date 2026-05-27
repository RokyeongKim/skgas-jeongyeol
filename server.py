import os
import re
from flask import Flask, request, jsonify, send_from_directory
from db import (init_db, save_case, get_all_cases, save_report, get_all_reports,
                update_case, delete_case, delete_report, save_recent_query, get_recent_queries)
from llm import get_recommendation
from search import get_embedding, find_similar_cases

app = Flask(__name__, static_folder='.', static_url_path='')
init_db()

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')


def parse_recommendation(text: str) -> dict:
    article   = re.search(r"\*\*추천 전결 조항:\*\*\s*(.+)", text)
    approver  = re.search(r"\*\*전결권자:\*\*\s*(.+)", text)
    line      = re.search(r"\*\*결재선:\*\*\s*(.+)", text)
    rationale = re.search(r"\*\*근거:\*\*\s*(.+)", text)
    note      = re.search(r"\*\*참고사항:\*\*\s*(.+)", text)
    return {
        "article":   article.group(1).strip()   if article   else "",
        "approver":  approver.group(1).strip()  if approver  else "",
        "line":      line.group(1).strip()      if line      else "",
        "rationale": rationale.group(1).strip() if rationale else "",
        "note":      note.group(1).strip()      if note      else "",
        "raw":       text,
    }


def check_admin():
    if not ADMIN_PASSWORD:
        return True
    return request.headers.get('X-Admin-Password', '') == ADMIN_PASSWORD


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/recommend', methods=['POST'])
def recommend():
    data    = request.json or {}
    name    = data.get('name', '')
    dept    = data.get('dept', '')
    summary = data.get('summary', '')
    bg      = data.get('background', '')

    raw = get_recommendation(summary, dept, bg)
    rec = parse_recommendation(raw)

    if rec.get('article'):
        save_recent_query(rec['article'])

    all_cases = get_all_cases()
    similar   = find_similar_cases(summary, all_cases)

    return jsonify({**rec, "similar": similar})


@app.route('/api/save', methods=['POST'])
def save():
    data = request.json or {}
    embedding = get_embedding(data.get('summary', ''))
    case_id = save_case(
        user_name=data.get('name', ''),
        department=data.get('dept', ''),
        approval_summary=data.get('summary', ''),
        adopted_article=data.get('article', ''),
        approval_line=data.get('line', ''),
        embedding=embedding,
        is_custom=data.get('is_custom', 0),
        deviation_reason=data.get('deviation_reason', ''),
        consulted_with=data.get('consulted_with', ''),
    )
    return jsonify({"ok": True, "id": case_id})


@app.route('/api/cases', methods=['GET'])
def cases():
    rows = get_all_cases()
    result = []
    for r in rows:
        c_id, ts, name, dept, summary, article, line, emb, is_custom, dev_reason, consulted = r
        result.append({
            "id":               c_id,
            "timestamp":        ts,
            "name":             name,
            "department":       dept,
            "summary":          summary,
            "article":          article,
            "line":             line,
            "is_custom":        bool(is_custom),
            "deviation_reason": dev_reason or '',
            "consulted_with":   consulted or '',
        })
    return jsonify(result)


@app.route('/api/cases/<int:case_id>', methods=['PATCH'])
def update_case_route(case_id):
    if not check_admin():
        return jsonify({"error": "관리자 권한이 필요합니다."}), 403
    data = request.json or {}
    update_case(
        case_id=case_id,
        approval_summary=data.get('summary', ''),
        adopted_article=data.get('article', ''),
        approval_line=data.get('line', ''),
        is_custom=data.get('is_custom', 0),
        deviation_reason=data.get('deviation_reason', ''),
        consulted_with=data.get('consulted_with', ''),
    )
    return jsonify({"ok": True})


@app.route('/api/cases/<int:case_id>', methods=['DELETE'])
def delete_case_route(case_id):
    if not check_admin():
        return jsonify({"error": "관리자 권한이 필요합니다."}), 403
    delete_case(case_id)
    return jsonify({"ok": True})


@app.route('/api/report', methods=['POST'])
def report():
    data = request.json or {}
    save_report(
        user_name=data.get('name', ''),
        department=data.get('dept', ''),
        content=data.get('content', ''),
    )
    return jsonify({"ok": True})


@app.route('/api/reports', methods=['GET'])
def get_reports():
    rows = get_all_reports()
    result = []
    for r in rows:
        r_id, ts, name, dept, content, status = r
        result.append({
            "id": r_id,
            "timestamp": ts,
            "name": name,
            "department": dept,
            "content": content,
            "status": status,
        })
    return jsonify(result)


@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
def delete_report_route(report_id):
    if not check_admin():
        return jsonify({"error": "관리자 권한이 필요합니다."}), 403
    delete_report(report_id)
    return jsonify({"ok": True})


@app.route('/api/recent_queries', methods=['GET'])
def recent_queries():
    rows = get_recent_queries(5)
    result = [{"article": article, "timestamp": ts} for article, ts in rows]
    return jsonify(result)


@app.route('/api/admin/verify', methods=['POST'])
def verify_admin():
    data = request.json or {}
    password = data.get('password', '')
    if not ADMIN_PASSWORD:
        return jsonify({"ok": True})
    if password == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "비밀번호가 올바르지 않습니다."}), 401


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
