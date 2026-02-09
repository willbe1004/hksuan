# Project Rainmaker 개발 기획서

## 1. 개요
- 목표: 공공입찰 공고(나라장터/세움터) 자동 수집 및 AI 분석 영업 자동화 웹앱
- 핵심: Python으로 수집/분석하고, Google Sheets에 저장하며, React 웹앱으로 보여준다.

## 2. 기술 스택
- Backend (수집기): Python (Selenium, Requests), Google Gemini API
- Frontend (웹앱): React (Vite), Tailwind CSS
- Database: Google Sheets (API 역할: Google Apps Script)
- Infrastructure: GitHub Actions (자동 실행), Vercel (웹 호스팅)

## 3. 폴더 구조
- /backend : Python 수집기 코드 (scraper.py, main.py 등)
- /frontend : React 웹앱 코드

## 4. 데이터 구조 (Google Sheets)
- 시트1 [Bids]: 공고번호, 공고명, 링크, 면적, 빗물저류조_대상여부(T/F), 상태
- 시트2 [Activities]: 활동일자, 내용, 담당자

## 5. 핵심 로직
1. 매일 아침 Python이 공고를 크롤링한다.
2. HWP 첨부파일 내용을 텍스트로 변환한다.
3. Gemini에게 "빗물저류조 의무 대상인가?"를 묻고 결과를 받는다.
4. 결과를 Google Sheets에 저장한다.
5. 사용자는 웹앱에서 이 리스트를 보고 영업 활동을 기록한다.