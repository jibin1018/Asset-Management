import datetime as dt

from sqlalchemy.orm import Session

from ..constants import ACCOUNT_TYPES
from ..models import Account, NetWorthSnapshot


def totals(accounts: list[Account]) -> tuple[int, int]:
    assets = debts = 0
    for a in accounts:
        if ACCOUNT_TYPES.get(a.type, {}).get("liability"):
            debts += abs(a.balance)
        else:
            assets += a.balance
    return assets, debts


def record_snapshot(db: Session) -> None:
    """오늘 날짜의 순자산 스냅샷을 갱신한다. 자산이 바뀔 때마다 호출."""
    assets, debts = totals(db.query(Account).all())
    db.merge(NetWorthSnapshot(date=dt.date.today(), assets=assets, debts=debts))
    db.commit()
