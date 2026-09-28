"""거래 내용(가맹점명/적요) 키워드로 분류를 자동 지정."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import CAT_MAP, DEFAULT_EXPENSE, DEFAULT_INCOME, DEFAULT_RULES
from ..models import CategoryRule

_DEFAULT_SORTED: list[tuple[str, str]] = sorted(
    ((kw.upper(), cat) for cat, kws in DEFAULT_RULES.items() for kw in kws),
    key=lambda r: -len(r[0]),
)


def kind_of(category: str) -> str:
    return CAT_MAP.get(category, {"kind": "expense"})["kind"]


def compatible(category: str, direction: int) -> bool:
    """입금에는 수입/이체 분류만, 출금에는 지출/이체 분류만 허용."""
    kind = kind_of(category)
    if kind == "transfer":
        return True
    return kind == ("income" if direction > 0 else "expense")


class Categorizer:
    def __init__(self, user_rules: list[tuple[str, str]] = ()):
        self.user = sorted(
            ((k.strip().upper(), c) for k, c in user_rules if k.strip()),
            key=lambda r: -len(r[0]),
        )

    def categorize(self, description: str, direction: int) -> str:
        text = (description or "").upper()
        for rules in (self.user, _DEFAULT_SORTED):
            for keyword, category in rules:
                if keyword in text and compatible(category, direction):
                    return category
        return DEFAULT_INCOME if direction > 0 else DEFAULT_EXPENSE


def build_categorizer(db: Session) -> Categorizer:
    rules = db.scalars(select(CategoryRule)).all()
    return Categorizer([(r.keyword, r.category) for r in rules])
