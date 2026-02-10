"""
나라장터 입찰공고 API 호출 및 데이터 파싱
검색 전용 PPSSrch 엔드포인트 사용 (웹 검색과 동일)
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
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

# 검색 전용 엔드포인트 (웹 검색과 동일, bidNtceNm 검색 지원)
BASE_URL = "https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch"
# 02 버전 500 시 폴백 (일부 환경에서 02 미지원)
BASE_URL_FALLBACK = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"


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
    나라장터 API 호출 - 검색 전용 PPSSrch 엔드포인트.
    - 수집 기간: 오늘 기준 최근 3개월 (동적 계산)
    - inqryDiv=1, bidNtceNm='설계' 유지
    """
    _load_env()
    api_key = os.getenv("NARA_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("NARA_API_KEY가 .env에 설정되지 않았습니다.")

    # 수집 기간: 시스템 시간 기준 최근 3개월 (동적 계산)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    inqry_bgn = start_date.strftime("%Y%m%d") + "0000"
    inqry_end = end_date.strftime("%Y%m%d") + "2359"
    print(f"[INFO] 수집 기간: {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')} (최근 3개월)")
    bid_ntce_nm = quote("설계")  # URL 인코딩 필수

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # ServiceKey에 +, / 등이 있으면 URL 인코딩 (500 방지)
    service_key_encoded = quote(api_key.strip(), safe="")
    base_params = (
        "?ServiceKey=" + service_key_encoded
        + "&inqryDiv=1"
        + "&bidNtceNm=" + bid_ntce_nm
        + "&pageNo=1"
        + "&numOfRows=100"
        + "&type=xml"
    )

    try:
        items = []
        # 1) 02 엔드포인트: 3개월 단일 호출
        full_url_02 = BASE_URL + base_params + "&inqryBgnDt=" + inqry_bgn + "&inqryEndDt=" + inqry_end
        resp = requests.get(full_url_02, headers=headers, verify=False, timeout=30)
        print(f"[DEBUG] API 호출(02): {inqry_bgn[:8]}~{inqry_end[:8]}, bidNtceNm=설계, status={resp.status_code}")

        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            result_code_el = root.find(".//resultCode")
            result_code = result_code_el.text if result_code_el is not None and result_code_el.text else ""
            if result_code in ("00", "0"):
                items = root.findall(".//item") or root.findall(".//{*}item")
                print(f"[DEBUG] API(02) 원시 item 총합: {len(items)}건")
            else:
                print(f"[DEBUG] 02 resultCode={result_code}, 응답:\n{resp.text[:1500]}")
        else:
            print(f"[DEBUG] 02 응답 본문(전체): {resp.text}")

        # 2) 02 실패 또는 0건 시 폴백: ad 서비스는 기간 2일 초과 시 07 에러 → 2일 단위 분할
        if not items:
            current = start_date
            while current <= end_date:
                week_end = min(current + timedelta(days=2), end_date)
                bgn = current.strftime("%Y%m%d") + "0000"
                end = week_end.strftime("%Y%m%d") + "2359"
                start_str, end_str = bgn[:8], end[:8]
                try:
                    full_url = BASE_URL_FALLBACK + base_params + "&inqryBgnDt=" + bgn + "&inqryEndDt=" + end
                    r = requests.get(full_url, headers=headers, verify=False, timeout=20)
                    if r.status_code != 200:
                        current = week_end + timedelta(days=1)
                        continue
                    rt = ET.fromstring(r.content)
                    rc = rt.find(".//resultCode")
                    if rc is not None and rc.text and rc.text not in ("00", "0"):
                        current = week_end + timedelta(days=1)
                        continue
                    its = rt.findall(".//item") or rt.findall(".//{*}item")
                    items.extend(its)
                    if its:
                        print(f"[DEBUG] 폴백 {start_str}~{end_str}: {len(its)}건")
                except (ET.ParseError, AttributeError, requests.RequestException, OSError) as e:
                    print(f"[ERROR] {start_str} ~ {end_str} 건너뜀 ({e})")
                except Exception as e:
                    print(f"[ERROR] {start_str} ~ {end_str} 건너뜀 ({e})")
                current = week_end + timedelta(days=1)
            print(f"[DEBUG] API(폴백) 원시 item 총합: {len(items)}건")

        if not items:
            print("[DEBUG] item 0건 → 02/폴백 모두 데이터 없음. (02 사용 시 마지막 응답 본문 확인)")
            if resp and getattr(resp, "text", None):
                print(resp.text[:2000])
    except ET.ParseError as e:
        print(f"[DEBUG] XML 파싱 실패: {e}\n응답 본문:\n{resp.text[:2000] if resp.text else '(empty)'}")
        return []
    except Exception as e:
        print(f"[DEBUG] 요청 예외: {e}")
        return []

    try:
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

            # 링크: API의 bidNtceDtlUrl 최우선, 없으면 bidPblancNo로 조립 (차수 -00 등은 태그 값이 정확함)
            link_el = item.find("bidNtceDtlUrl") or item.find("{*}bidNtceDtlUrl")
            link = (link_el.text or "").strip() if link_el is not None and link_el.text else ""
            if not link and bid_no:
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
