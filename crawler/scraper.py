"""
나라장터 입찰공고 API 호출 및 데이터 파싱
GAS와 동일한 엔드포인트: /ad/BidPublicInfoService, type=xml
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests
import urllib3

# SSL 경고 무시 (공공기관 접속 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2차 필터: 상세 키워드 - 이 중 하나라도 제목에 포함된 공고만
DETAIL_KEYWORDS = [
    "게이트볼", "경기장", "배드민턴", "체육", "테니스", "경찰서", "보건소",
    "커뮤니티센터", "주민센터", "행정복지센터", "건립", "건축", "도서관",
    "미술관", "병원", "복지관", "연구소", "주차장", "주차타워", "증축",
    "빗물", "저류", "우수", "침수",
]

# GAS와 동일: /ad/ 경로, 02 없음
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"


def _load_env():
    """프로젝트 루트의 .env 로드"""
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass


def fetch_nara_bids():
    """
    나라장터 API 호출 (GAS 동작 모방).
    - params 딕셔너리 사용하지 않음 (requests 인코딩 방지)
    - ServiceKey를 맨 앞에 두고 f-string으로 URL 직접 조립
    """
    _load_env()
    api_key = os.getenv("NARA_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("NARA_API_KEY가 .env에 설정되지 않았습니다.")

    # 날짜: 실행일 기준 과거 60일 00:00 ~ 오늘 23:59 (누락 방지, 중복은 sheet_manager에서 제거)
    today = datetime.now()
    start_date = today - timedelta(days=60)
    inqry_bgn = start_date.strftime("%Y%m%d") + "0000"
    inqry_end = today.strftime("%Y%m%d") + "2359"

    # [핵심] ServiceKey를 맨 앞에, 나머지 파라미터 뒤에. params 사용 안 함.
    # bidNtceNm 제거 (전체 조회 후 Python 필터링)
    full_url = (
        BASE_URL
        + "?ServiceKey="
        + api_key
        + "&inqryDiv=1"
        + "&inqryBgnDt=" + inqry_bgn
        + "&inqryEndDt=" + inqry_end
        + "&numOfRows=200"
        + "&pageNo=1"
        + "&type=xml"
    )

    print(f"[DEBUG] 최종 full_url:\n{full_url}\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    }

    try:
        response = requests.get(full_url, headers=headers, verify=False, timeout=10)

        print(f"[DEBUG] 응답 코드: {response.status_code}")

        if response.status_code != 200:
            print(f"[ERROR] 서버 응답 본문: {response.text[:300]}")
            return []

        # XML 파싱
        root = ET.fromstring(response.content)

        # 에러 메시지 확인
        err_msg = root.find(".//returnAuthMsg") or root.find(".//errMsg")
        if err_msg is not None and err_msg.text:
            print(f"[API ERROR] {err_msg.text}")
            return []

        # item 요소들 추출 (네임스페이스 고려)
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{*}item")

        print(f"[DEBUG] API 원시 item 수: {len(items)}")
        results = []
        for item in items:
            bid_name_el = item.find("bidNtceNm") or item.find("{*}bidNtceNm")
            bid_name = bid_name_el.text if bid_name_el is not None and bid_name_el.text else ""

            # 1차 필터: '설계' 없으면 continue
            if "설계" not in bid_name:
                continue

            # 2차 필터: DETAIL_KEYWORDS 중 하나라도 포함
            if not any(kw in bid_name for kw in DETAIL_KEYWORDS):
                continue

            bid_no_el = item.find("bidPblancNo") or item.find("bidNtceNo") or item.find("{*}bidPblancNo") or item.find("{*}bidNtceNo")
            bid_no = bid_no_el.text if bid_no_el is not None and bid_no_el.text else ""

            link = ""
            if bid_no:
                link = f"https://www.g2b.go.kr/ep/invitation/publish/bidPblancDtl.do?bidPblancNo={bid_no}"

            bid_dt_el = item.find("bidNtceDt") or item.find("{*}bidNtceDt")
            proc_el = item.find("cntrctCnclsMthdNm") or item.find("procMethod") or item.find("{*}cntrctCnclsMthdNm") or item.find("{*}procMethod")

            results.append({
                "bidNtceNo": str(bid_no),
                "bidNtceNm": bid_name,
                "bidNtceDt": bid_dt_el.text if bid_dt_el is not None and bid_dt_el.text else "",
                "procMethod": proc_el.text if proc_el is not None and proc_el.text else "",
                "link": link,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        print(f"[INFO] '설계' + 상세키워드 필터 통과: {len(results)}건")
        return results

    except ET.ParseError as e:
        print(f"[CRITICAL ERROR] XML 파싱 실패: {e}")
        return []
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        return []


def fetch_bids():
    """
    main.py 호환용 래퍼. (result_code, items) 튜플 반환.
    """
    try:
        items = fetch_nara_bids()
        return ("00", items) if items else ("03", [])
    except ValueError:
        raise
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        return ("HTTP_ERROR", [])


def parse_bid_row(item: dict) -> dict:
    """
    API 응답 항목을 Bids 시트 행 형식으로 변환합니다.
    fetch_nara_bids 결과는 이미 시트 형식이므로 collected_at만 보완.
    """
    collected_at = item.get("collected_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "bidNtceNo": str(item.get("bidNtceNo", "")),
        "bidNtceNm": item.get("bidNtceNm", ""),
        "bidNtceDt": item.get("bidNtceDt", ""),
        "procMethod": item.get("procMethod", ""),
        "link": item.get("link", ""),
        "collected_at": collected_at,
    }
