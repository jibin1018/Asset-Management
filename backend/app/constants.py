"""자산 유형, 거래 분류, 기본 자동분류 키워드."""

ACCOUNT_TYPES: dict[str, dict] = {
    "bank": {"label": "은행 입출금", "group": "cash"},
    "pay": {"label": "간편결제 머니", "group": "cash"},
    "saving": {"label": "예금·적금", "group": "saving"},
    "point": {"label": "포인트·마일리지", "group": "point"},
    "stock": {"label": "주식·증권", "group": "invest"},
    "fund": {"label": "펀드·ETF·연금", "group": "invest"},
    "crypto": {"label": "가상자산", "group": "invest"},
    "realestate": {"label": "부동산·보증금", "group": "real"},
    "other": {"label": "기타 자산", "group": "other"},
    "card": {"label": "신용카드 (미결제액)", "group": "debt", "liability": True},
    "loan": {"label": "대출", "group": "debt", "liability": True},
}

GROUPS: dict[str, dict] = {
    "cash": {"label": "현금성", "color": "#3b82f6"},
    "saving": {"label": "예·적금", "color": "#10b981"},
    "point": {"label": "포인트", "color": "#f59e0b"},
    "invest": {"label": "투자", "color": "#8b5cf6"},
    "real": {"label": "실물", "color": "#ec4899"},
    "other": {"label": "기타", "color": "#64748b"},
    "debt": {"label": "부채", "color": "#ef4444"},
}

# bucket: need(필수 지출) / want(선택 지출) — 50/30/20 분석에 사용
CATEGORIES: list[dict] = [
    {"name": "식비", "kind": "expense", "bucket": "need"},
    {"name": "카페·간식", "kind": "expense", "bucket": "want"},
    {"name": "배달", "kind": "expense", "bucket": "want"},
    {"name": "생활·마트", "kind": "expense", "bucket": "need"},
    {"name": "쇼핑", "kind": "expense", "bucket": "want"},
    {"name": "교통·차량", "kind": "expense", "bucket": "need"},
    {"name": "주거·공과금", "kind": "expense", "bucket": "need"},
    {"name": "통신", "kind": "expense", "bucket": "need"},
    {"name": "구독", "kind": "expense", "bucket": "want"},
    {"name": "의료·건강", "kind": "expense", "bucket": "need"},
    {"name": "보험", "kind": "expense", "bucket": "need"},
    {"name": "교육·자기계발", "kind": "expense", "bucket": "need"},
    {"name": "문화·여가", "kind": "expense", "bucket": "want"},
    {"name": "여행·숙박", "kind": "expense", "bucket": "want"},
    {"name": "경조사·선물", "kind": "expense", "bucket": "want"},
    {"name": "금융·수수료", "kind": "expense", "bucket": "need"},
    {"name": "기타지출", "kind": "expense", "bucket": "want"},
    {"name": "급여", "kind": "income"},
    {"name": "부수입", "kind": "income"},
    {"name": "이자·배당", "kind": "income"},
    {"name": "환급·기타수입", "kind": "income"},
    {"name": "내 계좌 이체", "kind": "transfer"},
    {"name": "저축·투자 이체", "kind": "transfer"},
    {"name": "카드대금", "kind": "transfer"},
]
CAT_MAP: dict[str, dict] = {c["name"]: c for c in CATEGORIES}
EXPENSE_CATEGORIES = [c["name"] for c in CATEGORIES if c["kind"] == "expense"]
WANT_CATEGORIES = {c["name"] for c in CATEGORIES if c.get("bucket") == "want"}

DEFAULT_EXPENSE = "기타지출"
DEFAULT_INCOME = "환급·기타수입"

# 거래 내용(가맹점/적요)에 키워드가 포함되면 해당 분류로. 긴 키워드가 먼저 매칭됨.
DEFAULT_RULES: dict[str, list[str]] = {
    "카페·간식": ["스타벅스", "투썸", "이디야", "메가MGC", "메가커피", "컴포즈", "빽다방", "할리스", "폴바셋",
               "커피", "카페", "파리바게뜨", "뚜레쥬르", "배스킨", "던킨", "베이커리"],
    "배달": ["배달의민족", "배민", "요기요", "쿠팡이츠", "땡겨요"],
    "생활·마트": ["이마트", "홈플러스", "롯데마트", "코스트코", "GS25", "CU", "씨유", "세븐일레븐", "이마트24",
               "다이소", "컬리", "편의점", "하나로마트"],
    "쇼핑": ["쿠팡", "11번가", "G마켓", "지마켓", "옥션", "무신사", "지그재그", "29CM", "에이블리", "SSG",
           "올리브영", "알리익스프레스", "테무", "스마트스토어", "아울렛", "백화점"],
    "교통·차량": ["카카오T", "카카오모빌리티", "택시", "티머니", "지하철", "버스", "코레일", "KTX", "SRT", "주유",
              "GS칼텍스", "SK에너지", "S-OIL", "현대오일뱅크", "하이패스", "주차", "쏘카", "그린카"],
    "주거·공과금": ["관리비", "월세", "도시가스", "한국전력", "한전", "수도요금", "전기요금"],
    "통신": ["SK텔레콤", "SKT", "KT", "LG유플러스", "LGU+", "알뜰폰", "통신요금"],
    "구독": ["넷플릭스", "NETFLIX", "유튜브", "YOUTUBE", "디즈니", "왓챠", "티빙", "웨이브", "멜론", "스포티파이",
           "SPOTIFY", "쿠팡와우", "네이버플러스", "APPLE.COM", "구글플레이", "GOOGLE", "OPENAI", "CHATGPT",
           "ANTHROPIC", "CLAUDE", "밀리의서재", "리디"],
    "의료·건강": ["병원", "의원", "약국", "치과", "한의원", "안과", "피부과", "헬스", "필라테스"],
    "보험": ["보험", "생명", "화재"],
    "교육·자기계발": ["학원", "인프런", "클래스101", "교보문고", "예스24", "알라딘", "유데미", "강의"],
    "문화·여가": ["CGV", "메가박스", "롯데시네마", "인터파크", "티켓링크", "노래방", "PC방", "볼링", "스팀", "STEAM"],
    "여행·숙박": ["대한항공", "아시아나", "제주항공", "진에어", "티웨이", "호텔", "에어비앤비", "AIRBNB", "야놀자",
              "여기어때", "아고다", "AGODA", "익스피디아"],
    "금융·수수료": ["수수료", "연회비", "대출이자"],
    "식비": ["식당", "김밥", "국밥", "맥도날드", "버거킹", "롯데리아", "맘스터치", "서브웨이", "치킨", "피자",
           "본죽", "한솥", "분식", "도시락"],
    "급여": ["급여", "월급", "상여"],
    "이자·배당": ["이자", "배당", "결산"],
    "카드대금": ["카드대금", "카드결제", "카드값", "신한카드", "삼성카드", "현대카드", "국민카드", "KB카드",
             "롯데카드", "하나카드", "우리카드", "BC카드", "NH카드"],
    "저축·투자 이체": ["적금", "청약", "증권", "키움", "미래에셋", "NH투자", "한국투자", "토스증권", "업비트",
                  "빗썸", "연금저축", "ISA", "IRP"],
}
