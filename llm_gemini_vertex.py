"""
Gemini Enterprise 버전 llm.py (Vertex AI 경로 - 사내 표준)

[사용 환경]
- 회사 GCP 프로젝트에서 Vertex AI 권한을 받은 경우 (Gemini Enterprise 표준 경로)
- 환경변수:
    GCP_PROJECT_ID = "회사-gcp-프로젝트-아이디"
    GCP_LOCATION   = "us-central1" 또는 "asia-northeast3" 등 회사 지정 리전
- 인증: 회사 PC에서 미리 한 번만 실행
    gcloud auth application-default login

[필요 패키지]
pip install google-cloud-aiplatform

[사용법]
기존 app.py / server.py 의 `from llm import get_recommendation` 부분을
`from llm_gemini_vertex import get_recommendation` 으로 바꾸기.
또는 이 파일을 llm.py 로 이름 바꿔서 덮어쓰기.
"""

import os
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

_regulation_text = None
_model = None


def load_regulation() -> str:
    global _regulation_text
    if _regulation_text is None:
        env_text = os.environ.get("REGULATION_TEXT", "")
        if env_text:
            _regulation_text = env_text
        else:
            reg_path = os.path.join(os.path.dirname(__file__), "docs", "전결규정.md")
            with open(reg_path, "r", encoding="utf-8") as f:
                _regulation_text = f.read()
    return _regulation_text


def _get_model():
    global _model
    if _model is None:
        vertexai.init(
            project=os.environ.get("GCP_PROJECT_ID", ""),
            location=os.environ.get("GCP_LOCATION", "us-central1"),
        )
        _model = GenerativeModel("gemini-2.5-pro")
    return _model


def get_recommendation(approval_summary: str, department: str, background: str = "") -> str:
    regulation = load_regulation()

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

    response = _get_model().generate_content(
        prompt,
        generation_config=GenerationConfig(
            max_output_tokens=1024,
            temperature=0.2,
        ),
    )
    return response.text
