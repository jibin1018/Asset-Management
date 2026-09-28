# 내 자산 관리 (Asset Manager)

은행 계좌, 간편결제 머니, 포인트, 주식·펀드·가상자산, 카드·대출까지 **모든 자산을 한곳에 모으고**,
거래내역을 자동 분류해 **지출을 점검하고 저축·절약 계획과 조언**을 제공하는 개인용 웹 시스템입니다.

- 백엔드: Python · FastAPI · SQLAlchemy · SQLite · pandas
- 프론트엔드: React · TypeScript · Vite · Recharts
- AI 조언 (선택): Anthropic Claude API

## 주요 기능

| 화면 | 기능 |
|---|---|
| 대시보드 | 순자산, 이번 달 수입·지출, 저축률, 자산 구성, 지출 분류, 6개월 추이, 순자산 변화, 핵심 점검 사항 |
| 자산 | 11가지 유형(은행, 페이 머니, 예·적금, 포인트, 주식, 펀드·연금, 가상자산, 부동산, 기타, 카드, 대출) 등록, 잔액 바로 수정, 투자 수익률, 이율, 포인트 소멸일 |
| 거래내역 | 기간·계좌·분류·검색 필터, 분류 변경(→ 같은 가맹점 규칙으로 저장), 직접 입력 |
| 내역 가져오기 | CSV / XLSX / XLS(HTML 형식 포함) / 엑셀 붙여넣기, 머리글 행·컬럼 자동 인식 및 수동 지정, 미리보기, 중복 제거 |
| 분석·조언 | 규칙 기반 진단(아래), 저축 계획(절감안 + 저축액 배분), 정기 결제·고정 지출 탐지, 분류별 추이, Claude 상담 |
| 예산·목표 | 분류별 월 예산(평균 기반 자동 설정), 저축 목표(계좌 연결, 월 필요액 계산) |
| 설정 | 목표 저축률·비상금 기준, 자동 분류 규칙, 백업/복원, 샘플 데이터 |

### 규칙 기반 진단 항목
저축률 대비 목표 · 지난달 대비 급증한 분류 · 예산 초과/임박 · 선택 지출 비중(50/30/20) · 카페·배달 소액 지출 ·
정기 결제 · 비상금(현금성 자산 ÷ 월평균 지출) · 이율 낮은 통장의 큰 잔액 · 포인트 소멸 예정 · 고금리 대출 ·
카드 미결제액 · 투자 비중 과다/과소 · 큰 손실 종목

## 실행 방법

필요: Python 3.10 이상, Node.js 18 이상

### 1. 백엔드

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API 문서: http://127.0.0.1:8000/docs
- 데이터는 `backend/data/assets.db`에 저장됩니다. 다른 위치를 쓰려면 `ASSET_DB_PATH` 환경변수를 지정하세요.

### 2. 프론트엔드 (개발 모드)

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 에 접속합니다. `/api` 요청은 Vite가 8000번 포트로 넘겨줍니다.
처음이라면 대시보드의 **샘플 데이터로 둘러보기**를 눌러 보세요.

### 3. 한 서버로 실행 (배포용)

```bash
cd frontend && npm run build        # frontend/dist 생성
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`frontend/dist`가 있으면 FastAPI가 화면까지 함께 제공합니다 → http://서버주소:8000

> ⚠️ 이 앱에는 로그인이 없습니다. 외부에 공개하지 말고 내 PC나 사설망에서만 쓰세요.
> 외부에서 접속해야 한다면 앞단에 인증(리버스 프록시 Basic Auth, Tailscale, Cloudflare Access 등)을 두세요.

### 테스트

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## AI 조언 켜기 (선택)

서버를 실행하기 전에 Anthropic API 키를 환경변수로 지정합니다.

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# macOS/Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

- 기본 모델은 `claude-opus-5`이며 `ANTHROPIC_MODEL` 환경변수로 바꿀 수 있습니다.
- 안전 분류기가 요청을 거절하면 서버 측에서 다른 모델로 자동 재시도하도록(`fallbacks: "default"`) 설정되어 있습니다.
- **원본 거래내역은 보내지 않습니다.** 월별·분류별 합계, 자산 유형별 잔액, 정기 결제 이름, 규칙 기반 진단 결과만 보냅니다
  (`backend/app/services/ai_advisor.py`의 `build_context`).
- 호출할 때마다 API 요금이 발생합니다.

## 거래내역 가져오기 팁

1. 은행 인터넷뱅킹 / 카드사 홈페이지에서 거래내역을 **엑셀로 저장**합니다. 간편결제·인터넷은행 앱도 내보내기 기능이 있으면 사용하세요.
2. 가져올 **계좌·카드를 선택**하고 파일을 올립니다. (은행 파일은 계좌별로, 카드 파일은 카드별로)
3. 머리글 행과 날짜/내용/금액 컬럼이 맞는지 확인합니다.
   - 은행: 출금·입금 컬럼이 따로 → "출금·입금 컬럼이 따로 있음"
   - 카드: 금액 하나, 양수가 결제 → "양수 = 지출"
4. 같은 파일을 다시 올려도 이미 있는 거래는 건너뜁니다.

**이중 계산 방지:** 은행 내역의 "카드대금", "적금/증권 이체"는 `이체` 분류로 들어가 수입·지출 통계에서 빠집니다.
카드 내역을 따로 가져오면 실제 사용처별 지출이 잡힙니다. 내 계좌끼리 옮긴 돈은 `내 계좌 이체`로 바꾸거나 설정에서 규칙을 추가하세요.

## 프로젝트 구조

```
backend/
  app/
    main.py              FastAPI 앱, 라우터 등록, 빌드된 프론트엔드 제공
    database.py          SQLite 연결
    models.py            Account, Transaction, CategoryRule, Budget, Goal, Setting, NetWorthSnapshot
    schemas.py           요청/응답 스키마
    constants.py         자산 유형, 분류, 기본 자동분류 키워드
    routers/             accounts, transactions, imports, analysis, planning, settings
    services/
      importer.py        파일 파싱, 머리글/컬럼 추정, 변환, 중복 판정
      categorizer.py     키워드 기반 자동 분류
      analysis.py        월별 집계, 조언 규칙, 저축 계획, 정기 결제 탐지
      ai_advisor.py      Claude 조언 (집계 데이터만 전송)
      sample.py          샘플 데이터
  tests/
frontend/
  src/
    pages/               Dashboard, Assets, Transactions, Import, Insights, Plan, Settings
    components/          Layout, 공통 UI, 차트
    context.tsx          전역 상태(기준 월, 메타데이터, 토스트), useApi 훅
```

## 한계와 다음 단계

- **자동 연동이 없습니다.** 국내에서 여러 금융사 데이터를 자동으로 모으는 마이데이터·오픈뱅킹 API는 허가받은 사업자만
  쓸 수 있어 개인 프로젝트에서는 파일 가져오기를 기본으로 했습니다. 자동화가 필요하면 금융 데이터 중개 API
  (예: CODEF 같은 스크래핑 API, 개인 개발자용 요금제·약관 확인 필요)를 붙일 수 있도록 `services/importer.py`의
  `convert` 결과 형식(dict 목록)에 맞춘 커넥터를 추가하면 됩니다.
- 잔액은 거래내역으로 자동 계산하지 않습니다(가져온 기간이 부분적일 수 있어서). 자산 화면에서 주기적으로 맞춰 주세요.
- 주식은 계좌 단위 평가금액만 관리합니다. 종목별 보유·시세 연동은 확장 과제입니다.
- 통화는 원화만 지원합니다.
- 로그인/다중 사용자가 없습니다.
