"""
Gemini 입찰 공고 분석 (gemini-flash-latest + 10초 대기 분당 6회 + 지수 백오프)
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

# 환경변수 로드 (프로젝트 루트 .env)
def _load_env():
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

_load_env()

# 별칭 사용 시 안정적인 최신 Flash로 자동 연결
GEMINI_MODEL = "models/gemini-flash-latest"

# 분당 6회 제한 (10초 대기)
TURTLE_DELAY_SEC = 10
MAX_RETRIES = 5
BACKOFF_BASE_SEC = 5
BACKOFF_MAX_SEC = 60


def analyze_bid(bid) -> dict:
    """
    공고를 분석하여 JSON 결과를 반환합니다. (속도 조절 + 지수 백오프 적용)
    :param bid: 공고 딕셔너리 (bidNtceNm, sucsfbidMthd 또는 procMethod 등)
    :return: {"rating": "S"|"A"|"B"|"C", "reason": "요약 사유"}
    """
    api_key = os.getenv("GEMINI_API_KEY") or ""
    if not api_key.strip():
        return {"rating": "C", "reason": "GEMINI_API_KEY 미설정"}

    bid_name = bid.get("bidNtceNm", "") if isinstance(bid, dict) else ""
    proc_method = bid.get("sucsfbidMthd") or bid.get("procMethod", "") if isinstance(bid, dict) else ""

    # 안정적 수집: 10초 대기 (분당 6회)
    print(f"⏳ 안정적 수집을 위해 10초 대기 중... ({(bid_name or '')[:10]}...)")
    time.sleep(TURTLE_DELAY_SEC)

    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
    genai.configure(api_key=api_key.strip())

    prompt = f"""
너는 입찰 분석 전문가야. 이 공고가 [건축/설계/감리]와 관련이 있고,
특히 '빗물저류조', '우수유출저감시설' 설계가 필요한지 판단해줘.

공고명: {bid_name or '(없음)'}
계약방법: {proc_method or '(없음)'}

반드시 아래 JSON 형식으로만 응답해. 다른 설명 없이 JSON만 출력.
{{"rating": "S", "reason": "한 줄 요약 사유"}}
rating 규칙: S=강력추천(빗물/저류조 명시), A=가능성 높음(건축/설계), B=보통, C=무관
"""

    model = genai.GenerativeModel(GEMINI_MODEL)

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            text = (response.text or "").strip()

            # 마크다운 코드블록 제거
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "", 1).replace("```", "").strip()

            # JSON 추출 (중괄호 구간)
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                obj = json.loads(text[start:end])
            else:
                obj = json.loads(text)

            rating = str(obj.get("rating", "C")).upper()
            if rating not in ("S", "A", "B", "C"):
                rating = "C"
            reason = str(obj.get("reason", ""))[:500] or "분석 완료"
            return {"rating": rating, "reason": reason}

        except ResourceExhausted as e:
            wait_time = min(BACKOFF_BASE_SEC * (2 ** attempt), BACKOFF_MAX_SEC)
            print(f"⚠️ [429 한도 초과] {wait_time}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
            if attempt >= MAX_RETRIES - 1:
                return {"rating": "C", "reason": "AI 429 한도 초과(재시도 소진)"}
            time.sleep(wait_time)
        except (json.JSONDecodeError, Exception) as e:
            wait_time = min(BACKOFF_BASE_SEC * (2 ** attempt), BACKOFF_MAX_SEC)
            print(f"⚠️ [AI 오류] {e} -> {wait_time}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
            if attempt >= MAX_RETRIES - 1:
                return {"rating": "C", "reason": f"AI 분석 실패: {str(e)[:150]}"}
            time.sleep(wait_time)

    return {"rating": "C", "reason": "AI 분석 실패 (API 오류)"}
