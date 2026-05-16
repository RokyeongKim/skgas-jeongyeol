import os
import anthropic

_regulation_text = None


def _get_api_key() -> str:
    # Streamlit Cloud secrets 우선, 없으면 환경변수 사용
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def load_regulation() -> str:
    global _regulation_text
    if _regulation_text is None:
        reg_path = os.path.join(os.path.dirname(__file__), "docs", "전결규정.md")
        with open(reg_path, "r", encoding="utf-8") as f:
            _regulation_text = f.read()
    return _regulation_text


def get_recommendation(approval_summary: str, department: str, background: str = "") -> str:
    regulation = load_regulation()
    client = anthropic.Anthropic(api_key=_get_api_key())

    prompt = f"""당신은 SK가스 전결규정 전문가입니다. 아래의 전결규정을 기반으로 품의 내용에 맞는 전결 조항과 결재선을 추천해 주세요.

## SK가스 전결규정
{regulation}

## 품의 정보
- 부서: {department}
- 품의 요지: {approval_summary}
- 배경/추가 설명: {background if background else "없음"}

## 답변 형식 (반드시 아래 형식 그대로 작성하세요)
**추천 전결 조항:** [첨부 번호 및 조항명 (예: 첨부1 5.3 예산집행)]
**전결권자:** [팀장 / 실장담당 / 본부장 / 대표이사 / 이사회 중 하나]
**결재선:** [예: 팀장 → 실장/담당 → 본부장]
**근거:** [어떤 조건(금액 기준, 행위 유형 등)에 해당하는지 구체적으로 설명]
**참고사항:** [협조 부서, 주의사항, 예외 규정 등. 없으면 "없음"]

---

※ 규정에 명확히 해당하는 조항이 없을 경우, 가장 유사한 조항을 제시하고 "⚠️ 규정 공백 가능성 있음" 문구를 추가하세요.
※ 금액이 언급된 경우 반드시 금액 기준에 따라 해당 구간을 명시하세요."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
