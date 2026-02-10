"""
Gemini Pro를 이용한 입찰 공고 가치 분석
"""
import json
import os
from pathlib import Path

PROMPT_TEMPLATE = """너는 입찰 분석 전문가야. 이 공고가 [건축/설계/감리]와 관련이 깊은지 판단하고, 수익성 가능성을 상/중/하로 평가해서 한 줄로 요약해줘.

공고명: {bid_title}
계약방법: {proc_method}

반드시 아래 JSON 형식으로만 응답해. 다른 설명 없이 JSON만 출력.
{{"rating": "S", "reason": "한 줄 요약 사유"}}
rating 규칙: S=상(수익성 높음), A=중상, B=중, C=하(수익성 낮음)"""


def _load_env():
    """프로젝트 루트의 .env 로드"""
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass


def analyze_bid(bid_title: str, proc_method: str) -> dict:
    """
    Gemini Pro로 공고를 분석하여 등급과 사유를 반환.

    :param bid_title: 공고명
    :param proc_method: 계약방법
    :return: {"rating": "S"|"A"|"B"|"C", "reason": "요약 사유"}
    """
    _load_env()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        return {"rating": "C", "reason": "GEMINI_API_KEY 미설정"}

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-pro")

        prompt = PROMPT_TEMPLATE.format(
            bid_title=bid_title or "(없음)",
            proc_method=proc_method or "(없음)",
        )
        response = model.generate_content(prompt)
        text = response.text.strip() if response.text else ""

        # JSON 추출 (마크다운 코드블록·여백 제거)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            obj = json.loads(text[start:end])
            rating = str(obj.get("rating", "C")).upper()
            if rating not in ("S", "A", "B", "C"):
                rating = "C"
            return {
                "rating": rating,
                "reason": str(obj.get("reason", ""))[:500] or "분석 완료",
            }

        return {"rating": "C", "reason": "AI 응답 파싱 실패"}
    except Exception as e:
        return {"rating": "C", "reason": f"AI 오류: {str(e)[:200]}"}
