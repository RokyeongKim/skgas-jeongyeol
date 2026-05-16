import streamlit as st
import re
from db import init_db, save_case, get_all_cases, save_report, get_all_reports, update_report_status
from llm import get_recommendation
from search import get_embedding, find_similar_cases

st.set_page_config(
    page_title="SK가스 전결 도우미",
    page_icon="📋",
    layout="wide",
)

init_db()

# --- 스타일 ---
st.markdown("""
<style>
.result-box {
    background: #f8f9fa;
    border-left: 4px solid #0066cc;
    padding: 1rem 1.2rem;
    border-radius: 4px;
    margin: 0.8rem 0;
    white-space: pre-wrap;
}
.similar-card {
    background: #fffbf0;
    border: 1px solid #e0c97a;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.9rem;
}
.badge-high { color: #0066cc; font-weight: bold; }
.badge-low  { color: #888; }
</style>
""", unsafe_allow_html=True)

st.title("📋 SK가스 전결 도우미")
st.caption("전결규정 기준: 35차 개정 (2026.02.11) · 개발: Project 9")

tab1, tab2, tab3 = st.tabs(["🔍 전결 조항 추천", "🚩 규정 공백 제보", "📂 사례 DB 조회"])

# =====================================================================
# TAB 1 — 전결 조항 추천
# =====================================================================
with tab1:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("품의 정보 입력")
        user_name   = st.text_input("담당자명", placeholder="예) 김노경")
        department  = st.text_input("부서명",   placeholder="예) 기획팀 / 재무팀 / LPG영업팀")
        approval_summary = st.text_area(
            "품의 요지",
            placeholder="예) 충전소 임차계약 체결, 보증금 2억원\n예) LNG 저장배관 계약 변경 (운영조건 변경)\n예) 운영예산 5,000만원 증액",
            height=120,
        )
        background = st.text_area(
            "배경 / 추가 설명 (선택)",
            placeholder="예) 기존 계약 만료로 신규 임차 필요, 인근 부지 신규 확보",
            height=80,
        )

        run_btn = st.button("🔍 전결 조항 추천받기", type="primary", use_container_width=True)

    with col_right:
        st.subheader("추천 결과")

        if run_btn:
            if not user_name or not department or not approval_summary:
                st.warning("담당자명, 부서명, 품의 요지를 모두 입력해 주세요.")
            else:
                # 유사 사례 먼저 조회
                all_cases = get_all_cases()
                similar = find_similar_cases(approval_summary, all_cases)

                if similar:
                    st.markdown("**🗂 유사 과거 사례**")
                    for s in similar:
                        st.markdown(f"""
<div class="similar-card">
  <b>{s['timestamp']}</b> · {s['department']} · 유사도 {s['similarity']}%<br>
  품의: {s['approval_summary']}<br>
  <span class="badge-high">채택 조항: {s['adopted_article']}</span> · 결재선: {s['approval_line']}
</div>""", unsafe_allow_html=True)
                    st.divider()

                with st.spinner("Claude가 전결규정을 검토 중입니다..."):
                    try:
                        result = get_recommendation(approval_summary, department, background)
                    except Exception as e:
                        st.error(f"오류 발생: {e}")
                        st.stop()

                st.session_state["last_result"]   = result
                st.session_state["last_summary"]  = approval_summary
                st.session_state["last_dept"]     = department
                st.session_state["last_user"]     = user_name

                st.markdown(f'<div class="result-box">{result}</div>', unsafe_allow_html=True)

                # 조항 확정 버튼 영역
                st.divider()
                st.markdown("**✅ 이 결과로 진행하시겠습니까?**")
                st.caption("확정하면 품의 요지·채택 조항·결재선이 사례 DB에 저장됩니다.")

                adopted_article = st.text_input(
                    "채택할 조항 (직접 입력 또는 위 결과 복사)",
                    key="adopted_input",
                    placeholder="예) 첨부4 4.1.1 토지/사무실 임대차계약 체결",
                )
                approval_line = st.text_input(
                    "결재선",
                    key="line_input",
                    placeholder="예) 팀장 → 본부장 → 대표이사",
                )

                if st.button("💾 확정 & DB 저장", use_container_width=True):
                    if not adopted_article or not approval_line:
                        st.warning("채택 조항과 결재선을 입력해 주세요.")
                    else:
                        emb = get_embedding(approval_summary)
                        save_case(user_name, department, approval_summary, adopted_article, approval_line, emb)
                        st.success("✅ 사례 DB에 저장되었습니다.")

        elif "last_result" in st.session_state:
            st.markdown(f'<div class="result-box">{st.session_state["last_result"]}</div>', unsafe_allow_html=True)


# =====================================================================
# TAB 2 — 규정 공백 제보
# =====================================================================
with tab2:
    st.subheader("🚩 규정 공백 / 모호한 케이스 제보")
    st.info("전결규정에 해당 케이스가 없거나 해석이 모호한 경우, 아래에 제보해 주세요. 연말 기획팀 검토 후 규정 개정에 반영됩니다.")

    with st.form("report_form"):
        r_name  = st.text_input("담당자명")
        r_dept  = st.text_input("부서명")
        r_content = st.text_area(
            "제보 내용",
            placeholder="예) OO 상황인데 어느 첨부의 어느 조항을 적용해야 할지 불명확함. 규정에 명시 없음.",
            height=150,
        )
        submitted = st.form_submit_button("제보하기", type="primary")

    if submitted:
        if not r_name or not r_dept or not r_content:
            st.warning("모든 항목을 입력해 주세요.")
        else:
            save_report(r_name, r_dept, r_content)
            st.success("✅ 제보가 접수되었습니다. 기획팀 검토 후 반영됩니다.")


# =====================================================================
# TAB 3 — 사례 DB 조회
# =====================================================================
with tab3:
    st.subheader("📂 사례 DB 조회")

    sub1, sub2 = st.tabs(["확정 사례 목록", "규정 공백 제보 목록"])

    with sub1:
        cases = get_all_cases()
        if not cases:
            st.info("저장된 사례가 없습니다. 전결 조항을 추천받고 확정하면 여기에 쌓입니다.")
        else:
            st.caption(f"총 {len(cases)}건")
            for case in cases:
                c_id, ts, name, dept, summary, article, line, _ = case
                with st.expander(f"[{ts}] {dept} · {summary[:40]}{'...' if len(summary)>40 else ''}"):
                    st.write(f"**담당자:** {name}")
                    st.write(f"**부서:** {dept}")
                    st.write(f"**품의 요지:** {summary}")
                    st.write(f"**채택 조항:** {article}")
                    st.write(f"**결재선:** {line}")

    with sub2:
        reports = get_all_reports()
        if not reports:
            st.info("접수된 제보가 없습니다.")
        else:
            st.caption(f"총 {len(reports)}건")
            for rep in reports:
                r_id, ts, name, dept, content, status = rep
                status_label = "✅ 처리완료" if status == "done" else "⏳ 검토대기"
                with st.expander(f"[{ts}] {dept} · {status_label}"):
                    st.write(f"**담당자:** {name}")
                    st.write(f"**부서:** {dept}")
                    st.write(f"**제보 내용:** {content}")
                    if status != "done":
                        if st.button("처리완료 표시", key=f"done_{r_id}"):
                            update_report_status(r_id, "done")
                            st.rerun()
