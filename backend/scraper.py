"""
나라장터 용역 입찰 공고 수집
"""
import os
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

# 2차 필터: 상세 키워드 - 이 중 하나라도 제목에 포함된 공고만 '돈이 되는 공고'
DETAIL_KEYWORDS = [
    "게이트볼",
    "경기장",
    "배드민턴",
    "체육",
    "테니스",
    "경찰서",
    "보건소",
    "커뮤니티센터",
    "주민센터",
    "행정복지센터",
    "건립",
    "건축",
    "도서관",
    "미술관",
    "병원",
    "복지관",
    "연구소",
    "주차장",
    "주차타워",
    "증축",
    "빗물",
    "저류",
    "우수",
    "침수",
]


def fetch_nara_bids() -> list[dict]:
    """
    나라장터 용역 입찰 공고를 가져오고, 상세 키워드로 필터링합니다.

    1차: API에서 bidNtceNm=설계로 '설계' 포함 공고만 요청
    2차: Python에서 상세 키워드 중 하나라도 제목에 포함된 공고만 반환

    Returns:
        필터링된 입찰 공고 목록 ('돈이 되는 공고')
    """
    service_key = os.getenv("NARA_API_KEY")
    if not service_key or not service_key.strip():
        raise ValueError("NARA_API_KEY가 .env에 설정되지 않았습니다. (Decoding 키 사용 필수)")

    # 조회 기간: 어제 00:00 ~ 오늘 23:59
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    inqry_bgn = yesterday.strftime("%Y%m%d") + "0000"
    inqry_end = today.strftime("%Y%m%d") + "2359"

    # 1차 API 검색: bidNtceNm=설계 (URL 인코딩)
    base_url = "https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServc02"
    bid_ntce_param = "&bidNtceNm=" + quote("설계")
    query = (
        f"?inqryDiv=1"
        f"&inqryBgnDt={inqry_bgn}"
        f"&inqryEndDt={inqry_end}"
        f"&numOfRows=100"
        f"&pageNo=1"
        f"&type=json"
        f"{bid_ntce_param}"
        f"&ServiceKey=" + service_key
    )
    url = base_url + query

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    # 응답 구조: response.body.items (단일 객체, 리스트, 또는 items.item)
    body = data.get("response", {}).get("body", {})
    items = body.get("items")

    if items is None or items == "":
        _print_result([])
        return []

    # items.item 형태로 감싸진 경우 (공공데이터 API 관례)
    if isinstance(items, dict) and "item" in items:
        items = items["item"]

    # API가 단일 객체로 반환하는 경우 리스트로 변환
    if isinstance(items, dict):
        items = [items]

    # 2차 키워드 필터링: 상세 키워드 중 하나라도 제목에 포함된 공고만
    filtered = [
        item
        for item in items
        if item.get("bidNtceNm")
        and any(kw in item.get("bidNtceNm", "") for kw in DETAIL_KEYWORDS)
    ]

    _print_result(filtered)
    return filtered


def _print_result(bids: list[dict]) -> None:
    """필터링된 '돈이 되는 공고'들의 제목만 출력합니다."""
    print()
    print("=" * 70)
    print("  [돈이 되는 공고] - 상세 키워드 필터 통과")
    print("=" * 70)

    if not bids:
        print("  (해당 기간에 조건에 맞는 공고가 없습니다)")
    else:
        for i, bid in enumerate(bids, 1):
            title = bid.get("bidNtceNm", "-")
            print(f"  [{i}] {title}")

    print("=" * 70)
    print(f"  총 {len(bids)}건")
    print("=" * 70)
