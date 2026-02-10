"""
Nara Market Crawler - 지휘관 (수집 -> DB 저장)
"""
import sys
from pathlib import Path

# 프로젝트 루트 기준 .env 로드
def _setup():
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass

_setup()

from scraper import fetch_nara_bids
from ai_analyst import analyze_bid
from sheet_manager import (
    log_to_sheet,
    save_bids_batch,
)


def run():
    """전체 크롤링 흐름: scraper -> sheet_manager"""
    try:
        log_to_sheet("INFO", "크롤러 시작", "main")

        # 1. scraper에서 데이터 수집
        items = fetch_nara_bids()

        if not items:
            log_to_sheet("INFO", "금일 신규 건수 없음", "main")
            return 0

        log_to_sheet("INFO", f"API 수집 {len(items)}건", "scraper")

        # 2. AI 분석: 각 공고에 rating, reason 추가 (results에 계속 담김)
        for r in items:
            result = analyze_bid(r.get("bidNtceNm", ""), r.get("procMethod", ""))
            r["AI_Rating"] = result.get("rating", "C")
            r["AI_Reason"] = result.get("reason", "")

        # 3. 시트 저장: 배치 1회 호출 (중복 제거 후 신규 건만 저장)
        count = save_bids_batch(items)
        if count == 0:
            log_to_sheet("INFO", "금일 신규 건수 없음 (전체 중복)", "sheet_manager")
        else:
            log_to_sheet("INFO", f"Bids 시트 저장 {count}건 완료 (AI 분석 포함)", "sheet_manager")
        return 0

    except FileNotFoundError as e:
        log_to_sheet("ERROR", str(e), "main")
        print(f"[오류] {e}")
        return 1
    except ValueError as e:
        log_to_sheet("ERROR", str(e), "main")
        print(f"[오류] {e}")
        return 1
    except Exception as e:
        log_to_sheet("ERROR", str(e), "main")
        print(f"[오류] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run())
