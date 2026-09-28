"""화면을 둘러볼 수 있는 가상 데이터 (최근 4개월)."""

import datetime as dt
import random

from sqlalchemy.orm import Session

from ..models import Account, Budget, CategoryRule, Goal, NetWorthSnapshot, Transaction
from .analysis import add_months, this_month
from .categorizer import Categorizer, kind_of
from .snapshots import record_snapshot


def clear_all(db: Session, commit: bool = True) -> None:
    for model in (Transaction, Goal, Budget, CategoryRule, NetWorthSnapshot, Account):
        db.query(model).delete()
    if commit:
        db.commit()


def load_sample(db: Session) -> None:
    clear_all(db)
    rnd = random.Random(42)
    today = dt.date.today()

    def acc(name, type_, inst, balance, **kw):
        a = Account(name=name, type=type_, institution=inst, balance=balance, **kw)
        db.add(a)
        return a

    next_month = add_months(this_month(), 1)
    main = acc("주거래 통장", "bank", "KB국민은행", 3_850_000, interest_rate=0.1)
    toss = acc("파킹통장", "bank", "토스뱅크", 6_200_000, interest_rate=2.0)
    kakao = acc("카카오페이머니", "pay", "카카오페이", 124_000)
    acc("네이버페이 포인트", "point", "네이버페이", 38_500, expire_date=dt.date.fromisoformat(f"{next_month}-15"))
    acc("OK캐쉬백", "point", "OK캐쉬백", 12_300)
    acc("청년도약계좌", "saving", "IBK기업은행", 8_400_000, interest_rate=4.5, monthly_payment=500_000)
    acc("주식 계좌", "stock", "키움증권", 12_750_000, principal=11_000_000)
    acc("연금저축펀드", "fund", "미래에셋증권", 5_300_000, principal=4_800_000)
    card = acc("신용카드", "card", "신한카드", 1_180_000)
    db.flush()

    cat = Categorizer()
    txs: list[Transaction] = []

    def add(date: dt.date, account: Account, amount: int, desc: str, direction: int):
        category = cat.categorize(desc, direction)
        txs.append(Transaction(date=date, account_id=account.id, amount=amount, direction=direction,
                               description=desc, category=category, kind=kind_of(category), source="sample"))

    for k in range(3, -1, -1):
        month = add_months(this_month(), -k)
        y, m = map(int, month.split("-"))
        last_day = (dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)).day
        if k == 0:
            last_day = today.day

        def on(day: int, account: Account, amount: int, desc: str, direction: int = -1):
            if day <= last_day:
                add(dt.date(y, m, day), account, amount, desc, direction)

        # 고정 수입·지출
        on(25, main, 3_450_000, "급여 (주)에이비씨", 1)
        on(26, main, 500_000, "청년도약계좌 적금")
        on(26, main, 300_000, "키움증권 이체")
        on(14, main, 1_050_000 + rnd.randint(0, 30) * 10_000, "신한카드 대금")
        on(20, main, 650_000, "월세")
        on(21, main, 120_000 + rnd.randint(0, 25) * 1_000, "관리비")
        on(22, main, 69_000, "SK텔레콤 통신요금")
        on(28, toss, 9_800 + rnd.randint(0, 20) * 100, "파킹통장 이자", 1)
        # 구독
        on(3, card, 17_000, "넷플릭스")
        on(5, card, 14_900, "유튜브 프리미엄")
        on(9, card, 7_890, "쿠팡와우 멤버십")
        on(12, card, 10_900, "멜론")
        on(15, card, 29_000, "OPENAI CHATGPT")
        on(18, card, 7_900, "왓챠")

        # 일상 지출 — 최근 달로 올수록 배달이 늘어나는 패턴
        delivery_p = 0.18 + (3 - k) * 0.08
        for day in range(1, last_day + 1):
            d = dt.date(y, m, day)
            weekend = d.weekday() >= 5
            if rnd.random() < 0.6:
                add(d, card, rnd.randint(20, 65) * 100, rnd.choice(["스타벅스 역삼점", "메가MGC커피", "투썸플레이스", "컴포즈커피"]), -1)
            if not weekend and rnd.random() < 0.75:
                add(d, card, rnd.randint(7, 13) * 1000, rnd.choice(["김밥천국", "본죽", "한솥도시락", "서브웨이", "맥도날드", "순대국밥 식당"]), -1)
            if not weekend:
                add(d, card, 2_900, "티머니 교통", -1)
            if rnd.random() < delivery_p:
                add(d, card, rnd.randint(15, 34) * 1000, rnd.choice(["배달의민족", "쿠팡이츠", "요기요"]), -1)
            if rnd.random() < 0.25:
                add(d, kakao, rnd.randint(15, 80) * 100, rnd.choice(["GS25", "CU", "세븐일레븐"]), -1)
            if rnd.random() < 0.12:
                add(d, card, rnd.randint(12, 90) * 1000, rnd.choice(["쿠팡", "무신사", "올리브영"]), -1)
            if rnd.random() < 0.08:
                add(d, card, rnd.randint(50, 150) * 1000, rnd.choice(["이마트", "홈플러스"]), -1)
            if rnd.random() < 0.1:
                add(d, card, rnd.randint(6, 20) * 1000, "카카오T 택시", -1)
            if weekend and rnd.random() < 0.3:
                add(d, card, rnd.randint(15, 60) * 1000, rnd.choice(["CGV", "노래방", "인터파크 티켓"]), -1)
    db.add_all(txs)

    db.add_all([
        Goal(name="비상금 1,000만원", target=10_000_000, current=0, account_id=toss.id),
        Goal(name="여름 유럽여행", target=4_000_000, current=1_200_000,
             deadline=dt.date(today.year + 1, 6, 30)),
    ])
    db.add_all([Budget(category="카페·간식", monthly_limit=100_000), Budget(category="배달", monthly_limit=150_000)])
    db.commit()
    record_snapshot(db)
