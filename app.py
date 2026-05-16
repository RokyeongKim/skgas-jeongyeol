import streamlit as st
import re
from db import init_db, save_case, get_all_cases, save_report, get_all_reports, update_report_status
from llm import get_recommendation
from search import get_embedding, find_similar_cases


def parse_recommendation(text: str) -> dict:
    article    = re.search(r"\*\*추천 전결 조항:\*\*\s*(.+)",  text)
    approver   = re.search(r"\*\*전결권자:\*\*\s*(.+)",        text)
    line       = re.search(r"\*\*결재선:\*\*\s*(.+)",          text)
    rationale  = re.search(r"\*\*근거:\*\*\s*(.+)",            text)
    note       = re.search(r"\*\*참고사항:\*\*\s*(.+)",        text)
    return {
        "article":   article.group(1).strip()   if article   else "",
        "approver":  approver.group(1).strip()  if approver  else "",
        "line":      line.group(1).strip()      if line      else "",
        "rationale": rationale.group(1).strip() if rationale else "",
        "note":      note.group(1).strip()      if note      else "",
    }


st.set_page_config(
    page_title="전결규정 자동응답 · SK가스",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<link rel="preconnect" href="https://cdn.jsdelivr.net" />
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css" />
<link rel="stylesheet"
  href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" />
<style>
/* ── Hide Streamlit chrome ─────────────────────────────────────────────── */
#MainMenu, header, footer                        { display: none !important; }
[data-testid="stHeader"]                         { display: none !important; }
[data-testid="stToolbar"]                        { display: none !important; }
[data-testid="stStatusWidget"]                   { display: none !important; }
[data-testid="collapsedControl"]                 { display: none !important; }
section[data-testid="stSidebar"]                 { display: none !important; }
[data-testid="stDecoration"]                     { display: none !important; }

/* ── Base ──────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box !important; }
html, body, .stApp {
  font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
               "Segoe UI", system-ui, sans-serif !important;
  background: #f4f6fa !important;
  color: #0d1733 !important;
  -webkit-font-smoothing: antialiased;
}
.main .block-container,
[data-testid="stMainBlockContainer"] {
  padding: 0 !important;
  max-width: 100% !important;
}

/* ── Tabs → nav bar ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: #ffffff;
  border-bottom: 1px solid #eef1f6;
  padding: 0 24px;
  gap: 2px;
  min-height: 56px;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}
.stTabs [data-baseweb="tab"] {
  height: 36px !important;
  padding: 0 14px !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: #3b4660 !important;
  background: transparent !important;
  border: none !important;
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  letter-spacing: -0.01em !important;
  white-space: nowrap !important;
}
.stTabs [data-baseweb="tab"]:hover      { background: #f4f6fa !important; }
.stTabs [aria-selected="true"]          { background: #0d1733 !important; color: #fff !important; }
.stTabs [data-baseweb="tab-highlight"]  { display: none !important; }
.stTabs [data-baseweb="tab-border"]     { display: none !important; }
.stTabContent                           { padding: 0 !important; }

/* ── Column gap ────────────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: stretch !important; }

/* ── Inputs ────────────────────────────────────────────────────────────── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 14px !important;
  border: 1px solid #e2e6ee !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  color: #0d1733 !important;
  letter-spacing: -0.01em !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: #0d1733 !important;
  box-shadow: 0 0 0 3px rgba(13,23,51,.08) !important;
}
div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stSelectbox"] label {
  font-size: 12px !important; font-weight: 600 !important;
  color: #3b4660 !important; letter-spacing: -0.01em !important;
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  margin-bottom: 4px !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 14px !important;
  border: 1px solid #e2e6ee !important;
  border-radius: 8px !important;
  background: #ffffff !important;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 13px !important; font-weight: 600 !important;
  height: 38px !important; border-radius: 8px !important;
  border: 1px solid #e2e6ee !important;
  background: #ffffff !important; color: #0d1733 !important;
  letter-spacing: -0.01em !important; transition: all .12s !important;
  padding: 0 16px !important;
}
.stButton > button:hover          { background: #f4f6fa !important; border-color: #cdd4e0 !important; }
.stButton > button[kind="primary"] {
  background: #0d1733 !important; color: #fff !important; border-color: #0d1733 !important;
}
.stButton > button[kind="primary"]:hover { background: #0a1f44 !important; border-color: #0a1f44 !important; }

/* ── Radio ──────────────────────────────────────────────────────────────── */
div[data-testid="stRadio"] > label {
  font-size: 12px !important; font-weight: 600 !important; color: #3b4660 !important;
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
}
div[data-testid="stRadio"] label {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 13px !important; color: #0d1733 !important;
}

/* ── Checkbox ────────────────────────────────────────────────────────────── */
div[data-testid="stCheckbox"] label {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 13px !important; color: #0d1733 !important;
}

/* ── Alerts ─────────────────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
  border-radius: 10px !important; border: none !important;
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 13px !important;
}
div.stSuccess { background: #e6f5ec !important; color: #0f7a3a !important; }
div.stWarning { background: #fbf2dc !important; color: #a36500 !important; }
div.stInfo    { background: #eaf0ff !important; color: #1f4ed8 !important; }
div.stError   { background: #fff0f0 !important; }

/* ── Expander ────────────────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
  border: 1px solid #eef1f6 !important; border-radius: 12px !important;
  background: #ffffff !important; box-shadow: 0 1px 2px rgba(13,23,51,.03) !important;
  margin-bottom: 8px !important;
}
div[data-testid="stExpander"] summary {
  font-weight: 600 !important; color: #0d1733 !important;
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
}
div[data-testid="stExpander"] p {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  font-size: 13px !important; color: #3b4660 !important;
}

/* ── Caption / markdown ──────────────────────────────────────────────────── */
p, .stMarkdown p {
  font-family: "Pretendard Variable", Pretendard, sans-serif !important;
  color: #0d1733 !important;
}
.stCaption { font-size: 12px !important; color: #7a849c !important; }

/* ── Form ────────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
  border: 1px solid #eef1f6 !important; border-radius: 12px !important;
  background: #ffffff !important; padding: 20px !important;
  box-shadow: 0 1px 2px rgba(13,23,51,.03) !important;
}

/* ── Spinner ─────────────────────────────────────────────────────────────── */
div[data-testid="stSpinner"] p { color: #1f4ed8 !important; }

/* ══════════════════════════════════════════════════════════════════════════
   CUSTOM COMPONENT STYLES
   ══════════════════════════════════════════════════════════════════════════ */

/* Brand header */
.hf-nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px; background: #ffffff;
  border-bottom: 1px solid #eef1f6;
}
.hf-brand { display: flex; align-items: center; gap: 10px; font-size: 14.5px; font-weight: 700; color: #0d1733; letter-spacing: -0.02em; }
.hf-logo  { width: 24px; height: 24px; border-radius: 7px; background: #0a1f44; color: #fff; display: inline-flex; align-items: center; justify-content: center; font-size: 11.5px; font-weight: 700; }

/* Panels */
.main-panel { padding: 24px 28px; background: #f4f6fa; min-height: calc(100vh - 56px); }
.side-panel { padding: 20px; background: #fafbfd; border-left: 1px solid #eef1f6; min-height: calc(100vh - 56px); }
.panel-head { padding-bottom: 14px; border-bottom: 1px solid #eef1f6; margin-bottom: 18px; }
.panel-head h3 { font-size: 15px; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 3px; }
.panel-sub { font-size: 12px; color: #7a849c; font-weight: 500; }

/* Cards */
.hf-card { background: #ffffff; border: 1px solid #eef1f6; border-radius: 12px; box-shadow: 0 1px 2px rgba(13,23,51,.03); padding: 22px 24px; margin-bottom: 14px; }
.hf-card-soft { background: #fafbfd; border: 1px solid #eef1f6; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }

/* Typography */
.hf-micro  { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: #7a849c; font-weight: 600; }
.hf-eyebrow { font-size: 12px; color: #7a849c; font-weight: 500; }
.mono      { font-family: "JetBrains Mono", ui-monospace, monospace !important; letter-spacing: 0 !important; }
.hf-arr    { color: #a8b0c2; margin: 0 6px; font-size: 11px; }
.hf-hl     { background: #eaf0ff; padding: 1px 5px; border-radius: 4px; color: #0d1733; font-weight: 500; }

/* Chips */
.hf-chip         { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; background: #f4f6fa; color: #3b4660; border: 1px solid #e2e6ee; margin: 2px 3px 2px 0; }
.hf-chip-success { background: #e6f5ec; color: #0f7a3a; border-color: transparent; }
.hf-chip-warn    { background: #fbf2dc; color: #a36500; border-color: transparent; }
.hf-chip-fill    { background: #0d1733; color: #fff;    border-color: #0d1733; }
.hf-chip-subtle  { background: #eaf0ff; color: #1f4ed8; border-color: transparent; }

/* Result card */
.hf-result { background: #ffffff; border: 1px solid #eef1f6; border-radius: 12px; overflow: hidden; margin: 14px 0; box-shadow: 0 1px 2px rgba(13,23,51,.03); }
.hf-result-hero { padding: 18px 22px; display: grid; grid-template-columns: auto 1fr auto; gap: 20px; align-items: center; border-bottom: 1px solid #eef1f6; }
.hf-result-footer { padding: 12px 22px; background: #fafbfd; font-size: 12.5px; color: #3b4660; }

/* Approval chain bubbles */
.chain-wrap { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.chain-step { padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 500; background: #f4f6fa; color: #3b4660; }
.chain-step.final { background: #0d1733; color: #fff; font-weight: 600; }

/* Save card */
.hf-save { background: #ffffff; border: 1px solid #eef1f6; border-radius: 12px; padding: 18px 20px; margin: 14px 0; box-shadow: 0 1px 2px rgba(13,23,51,.03); }
.hf-save h4 { font-size: 14px; font-weight: 600; margin: 0 0 12px; }

/* Info/warn banners */
.hf-info { display: flex; gap: 8px; align-items: flex-start; padding: 10px 14px; background: #eaf0ff; border-radius: 10px; font-size: 12.5px; color: #1f4ed8; line-height: 1.55; margin: 10px 0; }
.hf-warn { display: flex; gap: 8px; align-items: flex-start; padding: 12px 14px; background: #fbf2dc; border-radius: 10px; font-size: 12.5px; color: #a36500; line-height: 1.55; margin: 10px 0; }

/* Evidence table */
.hf-tbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; border-radius: 10px; overflow: hidden; border: 1px solid #eef1f6; }
.hf-tbl th { font-size: 11px; font-weight: 600; color: #7a849c; text-transform: uppercase; letter-spacing: .05em; padding: 9px 14px; text-align: left; background: #fafbfd; border-bottom: 1px solid #eef1f6; }
.hf-tbl td { padding: 10px 14px; border-bottom: 1px solid #eef1f6; color: #3b4660; }
.hf-tbl tr:last-child td { border-bottom: none; }
.hf-tbl tr.hit td { background: #eaf0ff !important; color: #0d1733 !important; font-weight: 600 !important; }

/* Similar cases */
.similar-item { background: #ffffff; border: 1px solid #eef1f6; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; }

/* Side tree rows */
.tree-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-top: 1px solid #eef1f6; }
.tree-row:first-child { border-top: none; }

/* DB table rows */
.db-case-row { background: #ffffff; border: 1px solid #eef1f6; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; cursor: pointer; }
.db-case-row:hover { border-color: #cdd4e0; background: #fafbfd; }
.db-case-row.custom { border-left: 3px solid #a36500; }

/* Gap list items */
.gap-item { background: #ffffff; border: 1px solid #eef1f6; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }

/* Shortcut row */
.kbd { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 4px; border: 1px solid #e2e6ee; border-bottom-width: 2px; border-radius: 5px; font-family: "JetBrains Mono", monospace; font-size: 10.5px; font-weight: 500; background: #fff; color: #7a849c; }
</style>
""", unsafe_allow_html=True)

# ── Brand header ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hf-nav">
  <div class="hf-brand">
    <div class="hf-logo">전</div>
    전결규정 자동응답
    <span class="mono" style="font-size:11px;color:#7a849c;font-weight:400;margin-left:6px">
      v35차 개정 · 2026.02.11
    </span>
  </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "   🔍  전결 조항 추천   ",
    "   🚩  규정 공백 제보   ",
    "   📂  사례 DB 조회   ",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — 전결 조항 추천
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    col_main, col_side = st.columns([3.2, 1.8])

    # ── LEFT: form or result ─────────────────────────────────────────────
    with col_main:
        st.markdown('<div class="main-panel">', unsafe_allow_html=True)

        has_result = "last_result" in st.session_state

        if not has_result:
            # ── INPUT FORM ───────────────────────────────────────────────
            st.markdown("""
<div class="panel-head">
  <h3>품의 정보 입력</h3>
  <div class="panel-sub">안건 정보를 입력하면 적합한 전결 조항과 결재선을 추천합니다</div>
</div>""", unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="hf-card">', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    user_name  = st.text_input("담당자명 *", placeholder="예) 김노경",   key="inp_name")
                with c2:
                    department = st.text_input("부서명 *",   placeholder="예) 기획팀",    key="inp_dept")
                approval_summary = st.text_area(
                    "품의 요지 *",
                    placeholder="예) 충전소 임차계약 체결, 보증금 2억원\n예) 노트북 5억원어치 구매 전결",
                    height=90, key="inp_summary",
                )
                background = st.text_area(
                    "배경 / 추가 설명 (선택)",
                    placeholder="예) 기존 계약 만료로 신규 임차 필요, 인근 부지 신규 확보",
                    height=72, key="inp_bg",
                )
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("""
<div class="hf-info">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:1px">
    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
  </svg>
  입력 정보는 추천 결과와 함께 사례 DB에 저장되며, 동일 유형 안건의 추천 정확도를 높이는 데 사용됩니다.
</div>""", unsafe_allow_html=True)

            run_btn = st.button(
                "🔍  전결 조항 추천받기",
                type="primary", use_container_width=True, key="run_btn",
            )

            if run_btn:
                if not user_name or not department or not approval_summary:
                    st.warning("담당자명, 부서명, 품의 요지를 모두 입력해 주세요.")
                else:
                    with st.spinner("Claude가 전결규정을 검토 중입니다..."):
                        try:
                            result = get_recommendation(approval_summary, department, background)
                        except Exception as e:
                            st.error(f"오류 발생: {e}")
                            st.stop()

                    parsed = parse_recommendation(result)
                    st.session_state.update({
                        "last_result":   result,
                        "last_summary":  approval_summary,
                        "last_dept":     department,
                        "last_user":     user_name,
                        "last_article":  parsed["article"],
                        "last_approver": parsed["approver"],
                        "last_line":     parsed["line"],
                        "last_rationale":parsed["rationale"],
                        "last_note":     parsed["note"],
                    })
                    st.rerun()

        else:
            # ── RESULT VIEW ──────────────────────────────────────────────
            result        = st.session_state["last_result"]
            approval_summary = st.session_state["last_summary"]
            department    = st.session_state["last_dept"]
            user_name     = st.session_state["last_user"]
            article       = st.session_state["last_article"]
            approver      = st.session_state["last_approver"]
            line_str      = st.session_state["last_line"]
            rationale     = st.session_state["last_rationale"]
            note          = st.session_state["last_note"]

            # Section header with "새 안건" button
            hc1, hc2 = st.columns([4, 1])
            with hc1:
                st.markdown(f"""
<div class="panel-head">
  <h3>{approval_summary[:50]}{'…' if len(approval_summary)>50 else ''}</h3>
  <div class="panel-sub">{department} · {user_name} · 방금</div>
</div>""", unsafe_allow_html=True)
            with hc2:
                if st.button("＋ 새 안건", key="new_case"):
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.rerun()

            # ── 유사 사례 ─────────────────────────────────────────────
            all_cases = get_all_cases()
            similar   = find_similar_cases(approval_summary, all_cases)
            if similar:
                st.markdown('<div class="hf-micro" style="margin-bottom:10px">유사 과거 사례</div>',
                            unsafe_allow_html=True)
                for s in similar:
                    st.markdown(f"""
<div class="similar-item">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
    <span class="hf-chip">{s['department']}</span>
    <span class="mono" style="font-size:11px;color:#7a849c">{s['timestamp']} · 유사도 {s['similarity']}%</span>
  </div>
  <div style="font-size:13px;font-weight:500;color:#0d1733;margin-bottom:3px">{s['approval_summary']}</div>
  <div style="font-size:12.5px;color:#3b4660">
    <span class="hf-chip-subtle" style="display:inline-flex;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:500">
      채택 조항: {s['adopted_article']}
    </span>
    &nbsp;결재선: {s['approval_line']}
  </div>
</div>""", unsafe_allow_html=True)
                st.markdown('<hr style="border:none;border-top:1px solid #eef1f6;margin:12px 0"/>', unsafe_allow_html=True)

            # ── Result hero card ──────────────────────────────────────
            chain_parts = [p.strip() for p in line_str.split("→")] if line_str else []
            chain_html  = "".join(
                f'<span class="chain-step{"  final" if i == len(chain_parts)-1 else ""}">{p}</span>'
                + (f'<span class="hf-arr">→</span>' if i < len(chain_parts)-1 else "")
                for i, p in enumerate(chain_parts)
            ) if chain_parts else line_str

            st.markdown(f"""
<div class="hf-result">
  <div class="hf-result-hero">
    <div>
      <div class="hf-micro">전결권자</div>
      <div style="font-size:26px;font-weight:700;letter-spacing:-0.03em;margin-top:4px;color:#0d1733">
        {approver or "확인 필요"}
      </div>
    </div>
    <div style="border-left:1px solid #eef1f6;padding-left:20px">
      <div class="hf-micro">결재선</div>
      <div class="chain-wrap">{chain_html or line_str}</div>
    </div>
    <div style="text-align:right;min-width:110px">
      <div class="mono" style="font-size:11.5px;color:#1f4ed8;font-weight:500">{article}</div>
    </div>
  </div>
  <div class="hf-result-footer">
    <span style="color:#7a849c">근거 —</span>&nbsp;{rationale}
  </div>
</div>""", unsafe_allow_html=True)

            # ── Claude 원문 (접힘) ────────────────────────────────────
            with st.expander("Claude 전체 답변 보기"):
                st.markdown(result)

            # ── 참고사항 ─────────────────────────────────────────────
            if note and note != "없음":
                st.markdown(f"""
<div class="hf-info">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:1px">
    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
  </svg>
  <div><b style="color:#0d1733">참고</b> — {note}</div>
</div>""", unsafe_allow_html=True)

            # ── SAVE SECTION ─────────────────────────────────────────
            st.markdown('<div class="hf-save">', unsafe_allow_html=True)
            st.markdown('<h4>💾 사례 DB에 저장하시겠습니까?</h4>', unsafe_allow_html=True)

            if article and line_str:
                st.markdown(f"""
<div style="background:#fafbfd;border:1px solid #eef1f6;border-radius:10px;padding:12px 14px;margin-bottom:12px;font-size:13px">
  <div style="margin-bottom:4px"><span class="hf-micro">추천 조항</span>&nbsp; {article}</div>
  <div><span class="hf-micro">추천 결재선</span>&nbsp; {line_str}</div>
</div>""", unsafe_allow_html=True)

                save_mode = st.radio(
                    "저장 방식",
                    ["추천대로 저장", "다른 결재선 적용"],
                    horizontal=True,
                    key="save_mode_radio",
                )
            else:
                st.warning("조항/결재선 자동 파싱 실패 — 직접 입력해 주세요.")
                article   = st.text_input("채택 조항",  key="manual_article",
                                          placeholder="예) 첨부4 1.4.1 구매계약체결")
                line_str  = st.text_input("결재선",     key="manual_line",
                                          placeholder="예) 팀장 → 본부장 → 대표이사")
                save_mode = "추천대로 저장"

            is_custom        = 0
            deviation_reason = ""
            consulted_with   = ""
            final_article    = article
            final_line       = line_str

            if save_mode == "다른 결재선 적용":
                is_custom = 1
                st.markdown("""
<div class="hf-warn" style="margin-bottom:12px">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:1px">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    <path d="M12 9v4M12 17h.01"/>
  </svg>
  추천 전결과 다른 결재선을 적용합니다. 예외 사유와 협의자가 함께 DB에 저장됩니다.
</div>""", unsafe_allow_html=True)
                dc1, dc2 = st.columns(2)
                with dc1:
                    final_article = st.text_input(
                        "실제 채택 조항 *", key="custom_article",
                        placeholder="예) 첨부4 1.4.1 구매계약체결",
                        value=article,
                    )
                with dc2:
                    final_line = st.text_input(
                        "실제 결재선 *", key="custom_line",
                        placeholder="예) 팀장 → 본부장",
                        value=line_str,
                    )
                deviation_reason = st.text_area(
                    "변경 사유 *", key="deviation_reason",
                    placeholder="예) 사업본부장 위임전결 협의 완료",
                    height=80,
                )
                consulted_with = st.text_input(
                    "기획팀 협의자 *", key="consulted_with",
                    placeholder="예) 홍길동 팀장",
                )

            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✅  확정 & DB 저장", type="primary", use_container_width=True, key="save_btn"):
                if not final_article or not final_line:
                    st.warning("조항과 결재선을 확인해 주세요.")
                elif is_custom and not deviation_reason:
                    st.warning("다른 결재선 적용 시 변경 사유를 입력해 주세요.")
                elif is_custom and not consulted_with:
                    st.warning("기획팀 협의자를 입력해 주세요.")
                else:
                    emb = get_embedding(approval_summary)
                    save_case(
                        user_name, department, approval_summary,
                        final_article, final_line, emb,
                        is_custom, deviation_reason, consulted_with,
                    )
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.success("✅ 사례 DB에 저장됐습니다. 새 안건을 입력하세요.")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── RIGHT: side panel ────────────────────────────────────────────────
    with col_side:
        st.markdown('<div class="side-panel">', unsafe_allow_html=True)

        has_result = "last_result" in st.session_state

        if not has_result:
            # Idle: recent + tree + shortcuts
            st.markdown("""
<div class="panel-head">
  <h3>근거 조문</h3>
  <div class="panel-sub">결과가 나오면 자동으로 표시됩니다</div>
</div>

<div class="hf-micro" style="margin-bottom:8px">최근 조회</div>
<div class="hf-card-soft" style="margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;font-weight:500">
    <span>첨부4 · 1.1 구매품의</span>
    <span class="mono" style="font-size:11px;color:#7a849c">2시간 전</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;font-weight:500;border-top:1px solid #eef1f6">
    <span>첨부4 · 1.4.1 구매계약체결</span>
    <span class="mono" style="font-size:11px;color:#7a849c">어제</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;font-weight:500;border-top:1px solid #eef1f6">
    <span>첨부1-2 계정과목별 집행전결</span>
    <span class="mono" style="font-size:11px;color:#7a849c">지난주</span>
  </div>
</div>

<div class="hf-micro" style="margin-bottom:8px">전결규정 트리</div>
<div class="hf-card-soft" style="margin-bottom:16px;padding:10px 14px">
  <div class="tree-row"><span class="mono" style="font-size:11px;color:#1f4ed8;width:40px">첨부1</span><span style="font-size:13px;color:#3b4660">계정과목별 집행전결권한표</span></div>
  <div class="tree-row"><span class="mono" style="font-size:11px;color:#1f4ed8;width:40px">첨부4</span><span style="font-size:13px;color:#3b4660">구매관리 전결권한표</span></div>
  <div class="tree-row"><span class="mono" style="font-size:11px;color:#1f4ed8;width:40px">첨부6</span><span style="font-size:13px;color:#3b4660">계약관리 규정</span></div>
  <div class="tree-row"><span class="mono" style="font-size:11px;color:#1f4ed8;width:40px">별표</span><span style="font-size:13px;color:#3b4660">투자사업관리규정</span></div>
</div>

<div class="hf-micro" style="margin-bottom:8px">단축키</div>
<div class="hf-card-soft">
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12.5px;color:#3b4660">
    <span>추천받기</span><span><span class="kbd">⌘</span> <span class="kbd">↵</span></span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12.5px;color:#3b4660;border-top:1px solid #eef1f6">
    <span>DB 저장</span><span><span class="kbd">⌘</span> <span class="kbd">S</span></span>
  </div>
</div>
""", unsafe_allow_html=True)

        else:
            # Evidence dock: show article + similar cases
            article  = st.session_state.get("last_article", "")
            line_str = st.session_state.get("last_line", "")

            st.markdown(f"""
<div class="panel-head">
  <h3>근거 조문</h3>
  <div class="panel-sub">{article if article else "추천 조항"}</div>
</div>
<div class="hf-micro" style="margin-bottom:8px">적용 조항</div>
<div class="hf-card" style="padding:14px 16px;margin-bottom:14px">
  <div style="font-size:14px;font-weight:700;letter-spacing:-0.02em;margin-bottom:4px">{article or "—"}</div>
  <div style="font-size:13px;color:#3b4660">{line_str or "—"}</div>
</div>
""", unsafe_allow_html=True)

            all_cases = get_all_cases()
            approval_summary = st.session_state.get("last_summary", "")
            similar   = find_similar_cases(approval_summary, all_cases)

            if similar:
                st.markdown(f'<div class="hf-micro" style="margin-bottom:8px">유사 사례 · {len(similar)}건</div>',
                            unsafe_allow_html=True)
                for s in similar:
                    st.markdown(f"""
<div class="similar-item">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <span style="font-size:13px;font-weight:500">{s['approval_summary'][:30]}{'…' if len(s['approval_summary'])>30 else ''}</span>
    <span class="mono" style="font-size:11px;color:#7a849c">{s['similarity']}%</span>
  </div>
  <div style="font-size:12px;color:#7a849c">{s['department']} · {s['timestamp']}</div>
  <div style="margin-top:6px">
    <span class="hf-chip" style="font-size:11px">{s['adopted_article']}</span>
  </div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
<div class="hf-card-soft" style="font-size:12.5px;color:#7a849c;text-align:center;padding:20px">
  유사 사례 없음<br>첫 번째 사례가 됩니다
</div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — 규정 공백 제보
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    col_form, col_gaps = st.columns([3.2, 1.8])

    with col_form:
        st.markdown("""
<div class="main-panel">
<div class="panel-head">
  <h3>규정 공백 / 모호한 케이스 제보</h3>
  <div class="panel-sub">현재 전결규정이 다루지 않는 안건을 기획팀에 전달합니다</div>
</div>
<div class="hf-info" style="margin-bottom:18px">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:1px">
    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
  </svg>
  제보된 안건은 익명·실명 선택 가능하며, 연말 전결규정 개편 시 기획팀이 일괄 검토합니다.
</div>
""", unsafe_allow_html=True)

        with st.form("report_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                r_name = st.text_input("담당자명 *")
            with fc2:
                r_dept = st.text_input("부서명 *")
            r_content = st.text_area(
                "제보 내용 *",
                placeholder="예) OO 상황인데 어느 첨부의 어느 조항을 적용해야 할지 불명확함. 규정에 명시 없음.",
                height=150,
            )
            submitted = st.form_submit_button(
                "📨  기획팀으로 제보하기", type="primary", use_container_width=True,
            )

        if submitted:
            if not r_name or not r_dept or not r_content:
                st.warning("모든 항목을 입력해 주세요.")
            else:
                save_report(r_name, r_dept, r_content)
                st.success("✅ 제보가 접수되었습니다. 기획팀 검토 후 반영됩니다.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_gaps:
        st.markdown('<div class="side-panel">', unsafe_allow_html=True)
        reports = get_all_reports()
        total   = len(reports)
        st.markdown(f"""
<div class="panel-head">
  <h3>누적된 제보 · {total}건</h3>
  <div class="panel-sub">연말 검토 대상</div>
</div>""", unsafe_allow_html=True)

        if not reports:
            st.markdown("""
<div class="hf-card-soft" style="text-align:center;padding:30px;font-size:13px;color:#7a849c">
  아직 접수된 제보가 없습니다
</div>""", unsafe_allow_html=True)
        else:
            for rep in reports:
                r_id, ts, name, dept, content, status = rep
                status_chip = (
                    '<span class="hf-chip hf-chip-success">처리완료</span>'
                    if status == "done"
                    else '<span class="hf-chip hf-chip-warn">검토대기</span>'
                )
                st.markdown(f"""
<div class="gap-item">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px">
    <div style="font-size:13px;font-weight:600">{content[:40]}{'…' if len(content)>40 else ''}</div>
    {status_chip}
  </div>
  <div style="font-size:12px;color:#7a849c">{dept} · {name} · {ts}</div>
</div>""", unsafe_allow_html=True)
                if status != "done":
                    if st.button("처리완료", key=f"done_{r_id}", use_container_width=True):
                        update_report_status(r_id, "done")
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — 사례 DB 조회
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="main-panel">', unsafe_allow_html=True)

    cases = get_all_cases()

    st.markdown(f"""
<div class="panel-head" style="display:flex;align-items:flex-end;justify-content:space-between">
  <div>
    <h3>사례 DB 조회</h3>
    <div class="panel-sub">저장된 전결 추천 사례 · 총 {len(cases)}건</div>
  </div>
</div>""", unsafe_allow_html=True)

    sub1, sub2 = st.tabs(["  ✅  확정 사례 목록  ", "  🚩  규정 공백 제보 목록  "])

    with sub1:
        if not cases:
            st.info("저장된 사례가 없습니다. 전결 조항을 추천받고 확정하면 여기에 쌓입니다.")
        else:
            for case in cases:
                c_id, ts, name, dept, summary, article, line, _, is_custom, dev_reason, consulted = case
                badge = ' <span class="hf-chip hf-chip-warn" style="font-size:11px">⚠ 변경적용</span>' if is_custom else ' <span class="hf-chip hf-chip-success" style="font-size:11px">추천 일치</span>'
                label = f"[{ts}] {dept} · {summary[:45]}{'…' if len(summary)>45 else ''}"
                if is_custom:
                    label += " ⚠️ 변경적용"
                with st.expander(label):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.markdown(f"**담당자** — {name}")
                        st.markdown(f"**부서** — {dept}")
                        st.markdown(f"**품의 요지** — {summary}")
                    with ec2:
                        st.markdown(f"**채택 조항** — {article}")
                        st.markdown(f"**결재선** — {line}")
                    if is_custom:
                        st.markdown("---")
                        st.markdown(f"⚠️ **변경 사유** — {dev_reason}")
                        st.markdown(f"👤 **기획팀 협의자** — {consulted}")

    with sub2:
        reports = get_all_reports()
        if not reports:
            st.info("접수된 제보가 없습니다.")
        else:
            for rep in reports:
                r_id, ts, name, dept, content, status = rep
                status_label = "✅ 처리완료" if status == "done" else "⏳ 검토대기"
                with st.expander(f"[{ts}] {dept} · {status_label}"):
                    st.markdown(f"**담당자** — {name}")
                    st.markdown(f"**부서** — {dept}")
                    st.markdown(f"**제보 내용** — {content}")
                    if status != "done":
                        if st.button("처리완료 표시", key=f"done2_{r_id}"):
                            update_report_status(r_id, "done")
                            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
