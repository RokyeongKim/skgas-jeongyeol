import os
import re
from flask import Flask, request, jsonify, send_from_directory
from db import init_db, save_case, get_all_cases, save_report, get_all_reports
from llm import get_recommendation
from search import get_embedding, find_similar_cases

app = Flask(__name__, static_folder='.', static_url_path='')

init_db()


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

    all_cases = get_all_cases()
    similar   = find_similar_cases(summary, all_cases)

    return jsonify({**rec, "similar": similar})


@app.route('/api/save', methods=['POST'])
def save():
    data = request.json or {}
    embedding = get_embedding(data.get('summary', ''))
    save_case(
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
    return jsonify({"ok": True})


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


@app.route('/api/report', methods=['POST'])
def report():
    data = request.json or {}
    save_report(
        user_name=data.get('name', ''),
        department=data.get('dept', ''),
        content=data.get('content', ''),
    )
    return jsonify({"ok": True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
