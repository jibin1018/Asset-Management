"""지출 분석, 규칙 기반 조언, 저축 계획.

개인 가계부 규모(수만 건 이하)를 가정해 요청마다 거래를 메모리로 읽어 계산한다.
"""

import datetime as dt
import math
from collections import defaultdict
from statistics import median
from typing import Optional

from sqlalchemy.orm import Session

from ..constants import ACCOUNT_TYPES, CAT_MAP, GROUPS, WANT_CATEGORIES
from ..models import Account, Budget, Goal, NetWorthSnapshot, Transaction
from ..schemas import SettingsModel
from .settings_store import get_settings
from .snapshots import totals

LEVEL_ORDER = {"danger": 0, "warn": 1, "info": 2, "good": 3}
CASH_TYPES = {"bank", "pay"}


# ---------- 날짜 도우미 ----------
def ym(d: dt.date) -> str:
    return d.strftime("%Y-%m")


def this_month() -> str:
    return ym(dt.date.today())


def add_months(month: str, k: int) -> str:
    y, m = map(int, month.split("-"))
    idx = y * 12 + (m - 1) + k
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def recent_months(month: str, n: int) -> list[str]:
    return [add_months(month, -i) for i in range(n - 1, -1, -1)]


def months_until(deadline: dt.date) -> int:
    today = dt.date.today()
    return max(1, (deadline.year - today.year) * 12 + deadline.month - today.month)


def merchant_key(desc: str) -> str:
    """지점번호·카드번호 같은 숫자/기호를 지워 같은 가맹점끼리 묶는다."""
    cleaned = "".join(" " if (ch.isdigit() or ch in "*#_/()[]-.") else ch for ch in desc or "")
    return " ".join(cleaned.split()).upper()


def advice(level: str, title: str, body: str, saving: Optional[int] = None) -> dict:
    return {"level": level, "title": title, "body": body, "saving": saving}


def won(n: float) -> str:
    return f"{round(n):,}원"


class Ctx:
    """한 요청 동안 사용할 데이터 묶음."""

    def __init__(self, db: Session):
        self.db = db
        self.txs: list[Transaction] = db.query(Transaction).all()
        self.accounts: list[Account] = db.query(Account).all()
        self.budgets: dict[str, int] = {b.category: b.monthly_limit for b in db.query(Budget).all()}
        self.goals: list[Goal] = db.query(Goal).all()
        self.settings: SettingsModel = get_settings(db)
        self._summaries: dict[str, dict] = {}

    # ----- 기간 -----
    def months(self) -> list[str]:
        return sorted({ym(t.date) for t in self.txs})

    def resolve_month(self, month: Optional[str]) -> str:
        if month:
            return month
        ms = self.months()
        return ms[-1] if ms else this_month()

    # ----- 월별 집계 -----
    def summary(self, month: str) -> dict:
        if month in self._summaries:
            return self._summaries[month]
        income = expense = transfer = count = 0
        by_cat: dict[str, int] = defaultdict(int)
        for t in self.txs:
            if ym(t.date) != month:
                continue
            count += 1
            if t.kind == "income":
                income += t.amount
            elif t.kind == "expense":
                expense += t.amount
                by_cat[t.category] += t.amount
            else:
                transfer += t.amount
        s = {
            "month": month,
            "income": income,
            "expense": expense,
            "net": income - expense,
            "transfer": transfer,
            "count": count,
            "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
        }
        self._summaries[month] = s
        return s

    def averages(self, month: str, n: int = 3) -> dict:
        """최근 n개월 평균. 선택 월이 진행 중인 이번 달이면 지난달까지로 계산."""
        base = add_months(month, -1) if month == this_month() else month
        sums = [s for s in (self.summary(m) for m in recent_months(base, n)) if s["count"]]
        if not sums and self.summary(month)["count"]:
            sums = [self.summary(month)]
        k = len(sums) or 1
        by_cat: dict[str, float] = defaultdict(float)
        for s in sums:
            for c, v in s["by_category"].items():
                by_cat[c] += v / k
        income = sum(s["income"] for s in sums) / k
        if income == 0 and self.settings.monthly_income:
            income = self.settings.monthly_income
        return {
            "months": len(sums),
            "income": round(income),
            "expense": round(sum(s["expense"] for s in sums) / k),
            "by_category": {c: round(v) for c, v in sorted(by_cat.items(), key=lambda kv: -kv[1])},
        }

    # ----- 자산 -----
    def net_worth(self) -> dict:
        by_group: dict[str, int] = defaultdict(int)
        for a in self.accounts:
            info = ACCOUNT_TYPES.get(a.type, ACCOUNT_TYPES["other"])
            if not info.get("liability"):
                by_group[info["group"]] += a.balance
        assets, debts = totals(self.accounts)
        return {"assets": assets, "debts": debts, "net": assets - debts, "by_group": dict(by_group)}

    def cash(self) -> int:
        return sum(a.balance for a in self.accounts if a.type in CASH_TYPES)

    def accounts_of(self, *types: str) -> list[Account]:
        return [a for a in self.accounts if a.type in types]

    # ----- 정기 결제 탐지 -----
    def subscriptions(self) -> list[dict]:
        ms = self.months()
        if not ms:
            return []
        since = add_months(ms[-1], -5)
        groups: dict[str, list[Transaction]] = defaultdict(list)
        for t in self.txs:
            if t.kind == "expense" and ym(t.date) >= since:
                key = merchant_key(t.description)
                if key:
                    groups[key].append(t)
        result = []
        for items in groups.values():
            by_month: dict[str, list[int]] = defaultdict(list)
            for t in items:
                by_month[ym(t.date)].append(t.amount)
            amounts = [t.amount for t in items]
            is_sub = any(t.category == "구독" for t in items)
            once_a_month = all(len(v) == 1 for v in by_month.values())
            stable = max(amounts) <= min(amounts) * 1.15
            if not (is_sub or (len(by_month) >= 2 and once_a_month and stable)):
                continue
            last = max(items, key=lambda t: t.date)
            monthly = int(median(amounts))
            result.append({
                "name": last.description,
                "category": last.category,
                "monthly": monthly,
                "annual": monthly * 12,
                "months": len(by_month),
                "last_date": last.date.isoformat(),
                "essential": CAT_MAP.get(last.category, {}).get("bucket") == "need",
            })
        return sorted(result, key=lambda r: -r["monthly"])

    def category_trend(self, month: str, n: int = 3) -> dict:
        months = recent_months(month, n)
        sums = [self.summary(m) for m in months]
        cats = sorted({c for s in sums for c in s["by_category"]}, key=lambda c: -sums[-1]["by_category"].get(c, 0))
        rows = [{"category": c, "values": [s["by_category"].get(c, 0) for s in sums]} for c in cats]
        return {"months": months, "rows": rows}


# ---------- 조언 ----------
def build_advice(ctx: Ctx, month: str) -> list[dict]:
    s = ctx.summary(month)
    prev = ctx.summary(add_months(month, -1))
    avg = ctx.averages(month)
    nw = ctx.net_worth()
    target_rate = ctx.settings.savings_target_rate
    items: list[dict] = []

    if not ctx.txs and not ctx.accounts:
        return [advice("info", "데이터가 없습니다", "자산을 등록하고 거래내역을 가져오면 분석을 시작합니다.")]

    # 1. 저축률
    if s["income"] > 0:
        rate = (s["income"] - s["expense"]) / s["income"] * 100
        if rate < 0:
            items.append(advice("danger", f"수입보다 {won(-s['net'])} 더 썼습니다",
                                "이번 달 지출이 수입을 넘었습니다. 아래 '줄일 수 있는 지출'부터 확인하세요."))
        elif rate < target_rate:
            items.append(advice("warn", f"저축률 {rate:.0f}% (목표 {target_rate:.0f}%)",
                                f"목표까지 월 {won(s['income'] * target_rate / 100 - s['net'])}을 더 남겨야 합니다."))
        else:
            items.append(advice("good", f"저축률 {rate:.0f}% — 목표 달성",
                                f"수입의 {rate:.0f}%를 남겼습니다. 남은 돈이 입출금 통장에 머물지 않게 자동이체로 옮겨 두세요."))
    elif s["count"]:
        items.append(advice("info", "이번 달 수입 내역이 없습니다",
                            "급여 통장 내역을 가져오거나 설정에서 월 수입을 입력하면 저축률을 계산합니다."))

    # 2. 전월 대비 급증한 분류
    if prev["count"]:
        for cat, cur in s["by_category"].items():
            before = prev["by_category"].get(cat, 0)
            diff = cur - before
            if diff >= 50000 and cur >= before * 1.3:
                items.append(advice("warn", f"{cat} 지출이 지난달보다 {won(diff)} 늘었습니다",
                                    f"{won(before)} → {won(cur)}. 일시적인 지출인지 확인하세요."))

    # 3. 예산 초과
    for cat, limit in ctx.budgets.items():
        spent = s["by_category"].get(cat, 0)
        if limit > 0 and spent > limit:
            items.append(advice("danger", f"{cat} 예산 초과 ({won(spent - limit)})",
                                f"예산 {won(limit)} 중 {won(spent)}을 썼습니다."))
        elif limit > 0 and spent >= limit * 0.8:
            items.append(advice("warn", f"{cat} 예산의 {spent / limit * 100:.0f}% 사용",
                                f"남은 예산 {won(limit - spent)}."))

    # 4. 선택 지출(want) 비중 — 50/30/20 기준
    income = s["income"] or avg["income"]
    want = sum(v for c, v in s["by_category"].items() if c in WANT_CATEGORIES)
    if income > 0 and want / income > 0.3:
        items.append(advice("warn", f"선택 지출이 수입의 {want / income * 100:.0f}%",
                            "50/30/20 원칙에서는 필수 50%, 선택 30%, 저축 20%를 권합니다. "
                            "카페·배달·쇼핑·구독·여가 지출을 먼저 점검하세요.",
                            saving=round((want - income * 0.3) * 12)))

    # 5. 카페·배달 같은 잦은 소액 지출
    small = [t for t in ctx.txs if ym(t.date) == month and t.category in ("카페·간식", "배달")]
    small_total = sum(t.amount for t in small)
    if small_total >= 100000:
        items.append(advice("info", f"카페·배달 {len(small)}회, {won(small_total)}",
                            "횟수를 절반으로 줄이면 1년에 아래 금액을 모을 수 있습니다.",
                            saving=round(small_total / 2 * 12)))

    # 6. 정기 결제
    subs = [x for x in ctx.subscriptions() if not x["essential"]]
    if subs:
        monthly = sum(x["monthly"] for x in subs)
        names = ", ".join(x["name"] for x in subs[:5])
        items.append(advice("info", f"정기 결제 {len(subs)}건, 월 {won(monthly)}",
                            f"{names}. 최근 한 달 안 쓴 서비스는 해지하세요.",
                            saving=None if monthly == 0 else monthly * 12))

    # 7. 비상금
    cash = ctx.cash()
    if avg["expense"] > 0:
        months_cover = cash / avg["expense"]
        goal = ctx.settings.emergency_months
        if months_cover < min(3, goal):
            items.append(advice("danger", f"비상금이 {months_cover:.1f}개월 치뿐입니다",
                                f"입출금·페이 잔액 {won(cash)} / 월평균 지출 {won(avg['expense'])}. "
                                f"최소 3개월, 권장 {goal:.0f}개월 치를 파킹통장이나 CMA에 모아 두세요."))
        elif months_cover < goal:
            items.append(advice("info", f"비상금 {months_cover:.1f}개월 치 (목표 {goal:.0f}개월)",
                                f"{won(goal * avg['expense'] - cash)}을 더 모으면 목표에 도달합니다."))
        elif months_cover > goal * 2:
            idle = cash - goal * avg["expense"]
            items.append(advice("info", f"입출금 통장에 여유 자금 {won(idle)}",
                                f"비상금 목표({goal:.0f}개월)를 넘는 돈입니다. 예금·적금이나 장기 투자로 옮기는 것을 고려하세요."))
        else:
            items.append(advice("good", f"비상금 {months_cover:.1f}개월 치 확보", "비상금 목표를 충족했습니다."))

    # 8. 이율 낮은 통장에 큰돈
    for a in ctx.accounts_of("bank"):
        if a.balance >= 3_000_000 and (a.interest_rate or 0) < 1:
            items.append(advice("info", f"'{a.name}' 잔액 {won(a.balance)}의 이율이 낮습니다",
                                "하루만 맡겨도 연 2% 안팎의 이자를 주는 파킹통장·CMA로 옮기면 이자를 더 받을 수 있습니다.",
                                saving=round(a.balance * 0.02)))

    # 9. 포인트
    points = ctx.accounts_of("point")
    for a in points:
        if a.expire_date and 0 <= (a.expire_date - dt.date.today()).days <= 60 and a.balance > 0:
            items.append(advice("warn", f"'{a.name}' {won(a.balance)} 소멸 예정 ({a.expire_date:%m월 %d일})",
                                "기한 전에 사용하거나 현금·다른 포인트로 전환하세요."))
    point_total = sum(a.balance for a in points)
    if point_total >= 10000:
        items.append(advice("info", f"포인트 {won(point_total)} 보유",
                            "생필품 결제에 쓰거나 현금 전환하면 그만큼 지출이 줄어듭니다."))

    # 10. 부채
    for a in ctx.accounts_of("loan"):
        if (a.interest_rate or 0) >= 5:
            items.append(advice("warn", f"'{a.name}' 금리 {a.interest_rate:.1f}%",
                                "예·적금 이자보다 대출 이자가 높다면 여유 자금으로 먼저 상환하는 편이 유리합니다.",
                                saving=round(abs(a.balance) * a.interest_rate / 100)))
    card_debt = sum(abs(a.balance) for a in ctx.accounts_of("card"))
    if income > 0 and card_debt > income * 0.5:
        items.append(advice("warn", f"카드 미결제액 {won(card_debt)} (월 수입의 {card_debt / income * 100:.0f}%)",
                            "카드 사용액이 수입의 절반을 넘습니다. 체크카드 병행이나 카드 한도 조정을 고려하세요."))

    # 11. 투자 비중
    if nw["assets"] > 0:
        invest = nw["by_group"].get("invest", 0)
        share = invest / nw["assets"] * 100
        if share > 70:
            items.append(advice("warn", f"투자 자산 비중 {share:.0f}%",
                                "시장 하락 시 손실이 커질 수 있습니다. 비상금과 안전자산 비중을 확인하세요."))
        elif share < 10 and avg["expense"] > 0 and cash >= avg["expense"] * 3:
            items.append(advice("info", f"투자 자산 비중 {share:.0f}%",
                                "비상금이 확보되어 있다면 연금저축·ISA처럼 세제 혜택이 있는 계좌로 장기 투자를 시작해 볼 수 있습니다."))
        for a in ctx.accounts_of("stock", "fund", "crypto"):
            if a.principal and a.principal > 0:
                ret = (a.balance - a.principal) / a.principal * 100
                if ret <= -20:
                    items.append(advice("warn", f"'{a.name}' 수익률 {ret:.0f}%",
                                        "손실이 큽니다. 처음 투자한 이유가 아직 유효한지, 비중이 지나치지 않은지 점검하세요."))

    return sorted(items, key=lambda x: LEVEL_ORDER[x["level"]])


# ---------- 저축 계획 ----------
def goal_status(ctx: Ctx, g: Goal) -> dict:
    current = g.current
    if g.account_id:
        acc = next((a for a in ctx.accounts if a.id == g.account_id), None)
        if acc:
            current = acc.balance
    remaining = max(0, g.target - current)
    months_left = months_until(g.deadline) if g.deadline else None
    monthly_needed = math.ceil(remaining / months_left) if months_left else None
    return {
        "id": g.id, "name": g.name, "target": g.target, "current": g.current, "deadline": g.deadline,
        "account_id": g.account_id, "effective_current": current,
        "progress": round(min(1.0, current / g.target) * 100, 1) if g.target else 0,
        "months_left": months_left, "monthly_needed": monthly_needed,
    }


def build_plan(ctx: Ctx, month: str) -> dict:
    avg = ctx.averages(month)
    income, expense = avg["income"], avg["expense"]
    surplus = income - expense
    target = round(income * ctx.settings.savings_target_rate / 100)

    # 목표 저축액에 못 미치면 선택 지출에서 최대 30%씩 줄이는 안을 만든다
    cuts = []
    gap = target - surplus
    if gap > 0:
        for cat, value in avg["by_category"].items():
            if gap <= 0:
                break
            if cat not in WANT_CATEGORIES or value < 10000:
                continue
            cut = min(math.ceil(value * 0.3 / 1000) * 1000, math.ceil(gap / 1000) * 1000)
            cuts.append({"category": cat, "current": value, "cut": cut, "suggested": value - cut})
            gap -= cut
    monthly_saving = max(0, surplus + sum(c["cut"] for c in cuts))

    # 배분: 비상금 → 목표 → 장기 투자 순
    allocation = []
    remaining = monthly_saving
    emergency_target = round(expense * ctx.settings.emergency_months)
    cash = ctx.cash()
    emergency_gap = max(0, emergency_target - cash)
    if emergency_gap > 0 and remaining > 0:
        amount = min(remaining * 0.5, emergency_gap)
        amount = max(10000, round(amount / 10000) * 10000)
        amount = min(amount, remaining)
        allocation.append({"name": "비상금 (파킹통장·CMA)", "amount": amount,
                           "note": f"약 {math.ceil(emergency_gap / amount)}개월 뒤 목표 {won(emergency_target)} 달성"})
        remaining -= amount
    goals = [goal_status(ctx, g) for g in ctx.goals]
    for g in sorted(goals, key=lambda x: x["months_left"] or 9999):
        if remaining <= 0 or g["effective_current"] >= g["target"]:
            continue
        need = g["monthly_needed"] or math.ceil((g["target"] - g["effective_current"]) / 12)
        amount = min(need, remaining)
        note = "기한 내 달성 가능" if amount >= need else f"월 {won(need - amount)} 부족 — 기한 연장이나 지출 절감 필요"
        allocation.append({"name": f"목표: {g['name']}", "amount": amount, "note": note})
        remaining -= amount
    if remaining > 0:
        allocation.append({"name": "장기 투자 (연금저축·ISA·IRP 등)", "amount": remaining,
                           "note": "세액공제·비과세 혜택이 있는 계좌를 먼저 채우는 것이 유리합니다"})

    return {
        "based_on_months": avg["months"],
        "income": income, "expense": expense, "surplus": surplus,
        "target_rate": ctx.settings.savings_target_rate, "target": target,
        "cuts": cuts, "monthly_saving": monthly_saving,
        "emergency": {"cash": cash, "target": emergency_target, "gap": emergency_gap},
        "allocation": allocation, "goals": goals,
    }


# ---------- 화면용 묶음 ----------
def dashboard(ctx: Ctx, month: str) -> dict:
    nw = ctx.net_worth()
    s = ctx.summary(month)
    prev = ctx.summary(add_months(month, -1))
    snapshots = ctx.db.query(NetWorthSnapshot).order_by(NetWorthSnapshot.date).all()
    return {
        "month": month,
        "net_worth": nw,
        "groups": [{"key": k, "label": GROUPS[k]["label"], "color": GROUPS[k]["color"], "value": v}
                   for k, v in nw["by_group"].items() if v > 0],
        "summary": s,
        "prev_summary": prev,
        "savings_rate": round((s["income"] - s["expense"]) / s["income"] * 100, 1) if s["income"] else None,
        "target_rate": ctx.settings.savings_target_rate,
        "monthly": [{"month": m, "income": ctx.summary(m)["income"], "expense": ctx.summary(m)["expense"]}
                    for m in recent_months(month, 6)],
        "snapshots": [{"date": x.date.isoformat(), "net": x.assets - x.debts} for x in snapshots[-180:]],
        "advice": build_advice(ctx, month)[:5],
    }


def insights(ctx: Ctx, month: str) -> dict:
    return {
        "month": month,
        "advice": build_advice(ctx, month),
        "plan": build_plan(ctx, month),
        "subscriptions": ctx.subscriptions(),
        "trend": ctx.category_trend(month),
        "averages": ctx.averages(month),
    }
