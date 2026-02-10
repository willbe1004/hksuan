"""
나라장터 API 엔드포인트 정밀 진단 스크립트
"""
import os
import re
import sys
from pathlib import Path

import requests

# Windows 콘솔 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# .env 로드
def _load_env():
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass

_load_env()

URL_CANDIDATES = [
    ("URL 1 (Service02 기본)", "http://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServc"),
    ("URL 2 (Service02 검색전용)", "http://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch"),
    ("URL 3 (Service02 신규)", "http://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServc02"),
    ("URL 4 (/ad/ 기존)", "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"),
    ("URL 5 (/ad/ PPSSrch)", "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"),
]

PARAMS = "inqryDiv=1&inqryBgnDt=202501010000&inqryEndDt=202501022359&numOfRows=10&type=xml"


def main():
    api_key = os.getenv("NARA_API_KEY")
    if not api_key or not api_key.strip():
        print("[ERROR] NARA_API_KEY가 .env에 없습니다.")
        return

    api_key = api_key.strip()
    print(f"[INFO] NARA_API_KEY 로드됨 (앞 8자: {api_key[:8]}...)\n")
    print("=" * 60)

    for name, base_url in URL_CANDIDATES:
        full_url = f"{base_url}?ServiceKey={api_key}&{PARAMS}"
        print(f"\n▶ {name}")
        print(f"URL: {base_url}")
        try:
            resp = requests.get(full_url, timeout=15)
            code = resp.status_code
            body_preview = resp.text[:200] if resp.text else "(빈 응답)"
            print(f"응답코드: {code}, 본문 앞 200자: {body_preview}")

            if code == 200 and "<resultCode>00</resultCode>" in resp.text:
                print("\n" + "🎉 정답 찾음! " * 5)
                print(f"✅ 성공 URL: {base_url}")
                m = re.search(r"<totalCount>(\d+)</totalCount>", resp.text)
                if m:
                    print(f"totalCount: {m.group(1)}")
                if "<totalCount>" in resp.text:
                    import re
                    m = re.search(r"<totalCount>(\d+)</totalCount>", resp.text)
                    if m:
                        print(f"totalCount: {m.group(1)}")
                return
        except Exception as e:
            print(f"응답코드: Exception, 본문 앞 200자: {e}")

    print("\n" + "=" * 60)
    print("[결과] 정상(resultCode 00) 응답 없음")


if __name__ == "__main__":
    main()
