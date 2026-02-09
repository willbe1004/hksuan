"""
구글 시트 연동 클라이언트
gspread 라이브러리를 이용해 Rainmaker_DB 시트에 연결합니다.
"""
from pathlib import Path

import gspread


def get_bids_worksheet():
    """
    Rainmaker_DB 시트의 Bids 탭(첫 번째 시트)을 반환합니다.

    Returns:
        gspread.Worksheet: Bids 워크시트 객체
    """
    credentials_path = Path(__file__).resolve().parent / "service_account.json"

    gc = gspread.service_account(filename=str(credentials_path))
    spreadsheet = gc.open("Rainmaker_DB")
    worksheet = spreadsheet.sheet1  # 첫 번째 탭 = Bids

    return worksheet


def get_existing_bid_numbers(worksheet) -> set[str]:
    """
    시트에 이미 있는 공고번호 목록을 반환합니다.

    Returns:
        set[str]: 기존 공고번호 집합
    """
    try:
        records = worksheet.get_all_records()
        if not records:
            return set()

        # get_all_records()는 dict 리스트 반환. '공고번호' 키 또는 첫 번째 열 사용
        existing = set()
        for row in records:
            bid_no = row.get("공고번호") or (list(row.values())[0] if row else None)
            if bid_no and str(bid_no).strip():
                existing.add(str(bid_no).strip())
        return existing
    except Exception:
        return set()


def append_bids(worksheet, rows: list[list]) -> None:
    """
    Bids 시트에 행을 추가합니다.

    Args:
        worksheet: Bids 워크시트
        rows: 추가할 행들의 리스트 (각 행은 [공고번호, 공고명, 링크, 면적, 빗물저류조_대상여부, 상태])
    """
    if not rows:
        return

    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
