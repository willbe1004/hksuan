# Nara Market Crawler (Phase 1)

나라장터 입찰공고 API를 호출하여 '설계' 키워드가 포함된 공고를 수집하고, 구글 스프레드시트에 저장합니다.

## 실행 방법

### 로컬 실행

```bash
# 프로젝트 루트에서
cd crawler
python main.py
```

### 환경 변수

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `NARA_API_KEY` | O | 나라장터 API 인증키 (Decoding 키 사용) |
| `SERVICE_ACCOUNT_PATH` | X | 서비스 계정 JSON 경로. 미설정 시 `backend/service_account.json` 등 자동 탐색 |
| `SPREADSHEET_NAME` | X | 구글 스프레드시트 이름. 기본값: `Rainmaker_DB` |

### .env 파일

프로젝트 루트에 `.env` 파일을 생성하고 다음을 설정하세요:

```
NARA_API_KEY=your_decoding_key_here
```

## Google Sheets 구조

- **Bids**: `bidNtceNo`, `bidNtceNm`, `bidNtceDt`, `procMethod`, `link`, `collected_at`
- **System_Logs**: `timestamp`, `level`, `module`, `message`, `error_code`

시트가 없으면 헤더를 포함해 자동 생성됩니다.

## GitHub Actions

매일 **06:00 KST**에 자동 실행됩니다.

### Secrets 설정

- `NARA_API_KEY`: 나라장터 API 키
- `SERVICE_ACCOUNT_JSON`: 서비스 계정 JSON을 **base64 인코딩**한 문자열

```bash
# base64 인코딩 예시
base64 -i service_account.json | tr -d '\n' | pbcopy
```

### 수동 실행

Actions 탭 → Daily Crawl - Nara Market → Run workflow

## 테스트 시나리오

- **Case A (정상)**: API 응답 코드 `00`, 데이터 존재 → 시트에 저장
- **Case B (데이터 없음)**: 응답 코드 `03` 또는 empty → "금일 신규 공고 없음" 로그, 정상 종료
- **Case C (에러)**: `10`/`11`/`12` 또는 HTTP 500 → System_Logs에 ERROR 기록
