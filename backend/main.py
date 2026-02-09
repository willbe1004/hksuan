"""
API 키 로드, 나라장터 입찰 공고 조회, 구글 시트 저장
"""
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Windows 콘솔 한글 출력
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gsheet_client import append_bids, get_bids_worksheet, get_existing_bid_numbers
from scraper import fetch_nara_bids

# 프로젝트 루트의 .env 로드 (backend에서 실행 시 상위 폴더 참조)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


def bids_to_dataframe(bids: list[dict]) -> pd.DataFrame:
    """
    나라장터 API 응답을 Bids 시트 형식의 DataFrame으로 변환합니다.
    시트 컬럼: 공고번호, 공고명, 링크, 면적, 빗물저류조_대상여부, 상태
    """
    if not bids:
        return pd.DataFrame(
            columns=["공고번호", "공고명", "링크", "면적", "빗물저류조_대상여부", "상태"]
        )

    rows = []
    for bid in bids:
        # 공고번호: bidPblancNo 또는 bidNtceNo
        bid_no = bid.get("bidPblancNo") or bid.get("bidNtceNo") or ""
        bid_name = bid.get("bidNtceNm", "")

        # 나라장터 상세 링크 (공고번호가 있으면 생성)
        link = ""
        if bid_no:
            link = f"https://www.g2b.go.kr/ep/invitation/publish/bidPblancDtl.do?bidPblancNo={bid_no}"

        rows.append(
            {
                "공고번호": str(bid_no),
                "공고명": bid_name,
                "링크": link,
                "면적": "",
                "빗물저류조_대상여부": "",
                "상태": "",
            }
        )

    return pd.DataFrame(rows)


def print_bids(bids: list[dict]) -> None:
    """공고명과 공고일시를 깔끔하게 출력합니다."""
    if not bids:
        print("조회된 공고가 없습니다. (입찰공고명에 '설계'가 포함된 건만 표시)")
        return

    print()
    print("=" * 70)
    print("  나라장터 용역 입찰 공고 (설계 포함)")
    print("=" * 70)

    for i, bid in enumerate(bids, 1):
        name = bid.get("bidNtceNm", "-")
        date = bid.get("bidNtceDt", "-")
        print(f"  [{i}] 공고명: {name}")
        print(f"      공고일시: {date}")
        print()

    print("=" * 70)
    print(f"  총 {len(bids)}건")
    print("=" * 70)


if __name__ == "__main__":
    try:
        # 1. 나라장터에서 공고 가져오기 (필터링된 '돈이 되는 공고' 제목은 scraper에서 출력)
        bids = fetch_nara_bids()

        # 2. DataFrame으로 변환
        df = bids_to_dataframe(bids)
        if df.empty:
            print("추가할 공고가 없습니다.")
            exit(0)

        # 3. 구글 시트 연결 및 중복 체크
        worksheet = get_bids_worksheet()
        existing_nos = get_existing_bid_numbers(worksheet)

        # 4. 중복 제외 - 공고번호 기준
        df_new = df[~df["공고번호"].astype(str).str.strip().isin(existing_nos)]

        if df_new.empty:
            print("이미 등록된 공고만 있어 추가할 새 공고가 없습니다.")
            exit(0)

        # 5. 시트에 추가 (헤더 제외, 값만)
        rows_to_append = df_new.values.tolist()
        append_bids(worksheet, rows_to_append)

        print()
        print("구글 시트 저장 완료!")
        print(f"  - 추가된 공고: {len(df_new)}건")

    except ValueError as e:
        print(f"[오류] {e}")
        exit(1)
    except Exception as e:
        print(f"[오류] {e}")
        exit(1)
