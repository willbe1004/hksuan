"""
구글 시트 연결, 중복 체크, 데이터 저장, 로그 저장
"""
import os
from datetime import datetime
from pathlib import Path

import gspread

BIDS_HEADERS = ["bidNtceNo", "bidNtceNm", "bidNtceDt", "procMethod", "link", "collected_at", "AI_Rating", "AI_Reason"]
LOG_HEADERS = ["timestamp", "level", "module", "message"]


def _get_credentials_path() -> Path:
    """service_account.json 경로 탐색 (환경변수 > backend > crawler > 상위)"""
    env_path = os.getenv("SERVICE_ACCOUNT_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    base = Path(__file__).resolve().parent
    candidates = [
        base.parent / "backend" / "service_account.json",
        base / "service_account.json",
        base.parent / "service_account.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("service_account.json을 찾을 수 없습니다. SERVICE_ACCOUNT_PATH 환경변수를 설정하세요.")


def _get_spreadsheet_name() -> str:
    return os.getenv("SPREADSHEET_NAME", "Rainmaker_DB")


def get_client():
    """gspread 클라이언트 반환"""
    cred_path = _get_credentials_path()
    return gspread.service_account(filename=str(cred_path))


def ensure_headers(worksheet, headers: list[str]) -> None:
    """시트에 헤더가 없으면 생성, AI_Rating이 없으면 맨 끝에 AI_Rating·AI_Reason 추가"""
    try:
        first_row = worksheet.row_values(1)
        if not first_row:
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
        else:
            # AI_Rating이 없으면 헤더 맨 끝에 추가
            if "AI_Rating" not in first_row:
                col_count = len(first_row)
                worksheet.update_cell(1, col_count + 1, "AI_Rating")
                worksheet.update_cell(1, col_count + 2, "AI_Reason")
    except Exception:
        worksheet.append_row(headers, value_input_option="USER_ENTERED")


def get_bids_sheet():
    """Bids 시트 반환 (없으면 생성)"""
    gc = get_client()
    name = _get_spreadsheet_name()
    try:
        ss = gc.open(name)
    except gspread.SpreadsheetNotFound:
        raise FileNotFoundError(f"스프레드시트 '{name}'를 찾을 수 없습니다. 공유 링크에 서비스 계정 이메일을 추가하세요.")

    try:
        ws = ss.worksheet("Bids")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title="Bids", rows=100, cols=len(BIDS_HEADERS))
        ensure_headers(ws, BIDS_HEADERS)

    ensure_headers(ws, BIDS_HEADERS)
    return ws


def get_logs_sheet():
    """System_Logs 시트 반환 (없으면 생성)"""
    gc = get_client()
    name = _get_spreadsheet_name()
    ss = gc.open(name)

    try:
        ws = ss.worksheet("System_Logs")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title="System_Logs", rows=500, cols=len(LOG_HEADERS))
        ensure_headers(ws, LOG_HEADERS)

    ensure_headers(ws, LOG_HEADERS)
    return ws


def get_existing_bid_nos(bids_ws) -> set[str]:
    """Bids 시트의 bidNtceNo 열을 Set으로 반환 (중복 방지용)"""
    try:
        records = bids_ws.get_all_records()
        existing = {
            str(r.get("bidNtceNo", "")).strip()
            for r in records
            if r.get("bidNtceNo") and str(r.get("bidNtceNo")).strip()
        }
        return existing
    except Exception:
        return set()


def _bid_to_row(r: dict) -> list:
    """딕셔너리 한 건을 Bids 시트 행(리스트)으로 변환"""
    return [
        r.get("bidNtceNo", ""),
        r.get("bidNtceNm", ""),
        r.get("bidNtceDt", ""),
        r.get("procMethod", ""),
        r.get("link", ""),
        r.get("collected_at", ""),
        r.get("AI_Rating", ""),
        r.get("AI_Reason", ""),
    ]


def append_bids(bids_ws, rows: list[dict]) -> int:
    """Bids 시트에 행 추가 (한 건씩 append_row). 내부/레거시용. 배치는 save_bids_batch 사용."""
    if not rows:
        return 0
    for r in rows:
        bids_ws.append_row(_bid_to_row(r), value_input_option="USER_ENTERED")
    return len(rows)


def save_bids_batch(bids_list: list[dict]) -> int:
    """
    Bids 시트에 신규 건만 한 번에 배치 저장 (API 호출 1회).
    - 리스트 비어 있으면 바로 0 반환.
    - 기존 시트의 bidNtceNo를 get_all_values()로 한 번만 읽어 중복 제거 후, 진짜 신규 건만 append_rows.
    """
    if not bids_list:
        return 0

    ws = get_bids_sheet()
    try:
        all_values = ws.get_all_values()
    except Exception:
        all_values = []

    # 헤더 제외, 첫 번째 열(bidNtceNo)만 set으로
    existing = set()
    if len(all_values) > 1:
        for row in all_values[1:]:
            if row and len(row) > 0 and str(row[0]).strip():
                existing.add(str(row[0]).strip())

    new_only = [r for r in bids_list if str(r.get("bidNtceNo", "")).strip() not in existing]
    if not new_only:
        return 0

    rows = [_bid_to_row(r) for r in new_only]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def log_to_sheet(level: str, msg: str, module: str = "crawler") -> None:
    """System_Logs 탭에 [시간, 레벨, 모듈, 메시지] 한 줄 추가"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [ts, level, module, msg]

    try:
        logs_ws = get_logs_sheet()
        logs_ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"[Sheet Log Failed] {e}")

    print(f"[{ts}] [{level}] [{module}] {msg}")
