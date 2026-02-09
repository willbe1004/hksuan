"""
구글 시트 연결, 중복 체크, 데이터 저장, 로그 저장
"""
import os
from datetime import datetime
from pathlib import Path

import gspread

BIDS_HEADERS = ["bidNtceNo", "bidNtceNm", "bidNtceDt", "procMethod", "link", "collected_at"]
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
    """시트에 헤더가 없으면 생성"""
    try:
        first_row = worksheet.row_values(1)
        if not first_row:
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
        elif first_row != headers:
            # 기존 헤더가 다르면 그대로 사용 (덮어쓰지 않음)
            pass
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


def append_bids(bids_ws, rows: list[dict]) -> int:
    """Bids 시트에 행 추가 (append_row). 추가된 건수 반환."""
    if not rows:
        return 0

    for r in rows:
        row = [r.get(h, "") for h in BIDS_HEADERS]
        bids_ws.append_row(row, value_input_option="USER_ENTERED")
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
