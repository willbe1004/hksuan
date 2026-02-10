"""
오늘자(2026-02-10) 데이터 원본 확인 - 필터 없이 전체 조회
"""
import os
import sys
from pathlib import Path

import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def _load_env():
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass


def main():
    _load_env()
    api_key = os.getenv("NARA_API_KEY")
    if not api_key or not api_key.strip():
        print("[ERROR] NARA_API_KEY가 .env에 없습니다.")
        return

    url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = (
        "ServiceKey=" + api_key.strip()
        + "&inqryDiv=1"
        + "&inqryBgnDt=202602100000"
        + "&inqryEndDt=202602102359"
        + "&numOfRows=10"
        + "&pageNo=1"
        + "&type=xml"
    )
    full_url = f"{url}?{params}"

    print(f"[요청] {url}")
    print(f"[파라미터] inqryBgnDt=202602100000, inqryEndDt=202602102359, numOfRows=10 (bidNtceNm 없음)\n")
    print("=" * 60)
    print("[응답 XML 원본]")
    print("=" * 60)

    try:
        resp = requests.get(full_url, timeout=15)
        print(f"응답코드: {resp.status_code}\n")
        print(resp.text)
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    main()
