from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..constants import ACCOUNT_TYPES, CATEGORIES, GROUPS
from ..database import get_db
from ..models import Account, Transaction
from ..schemas import AccountIn, AccountOut, BalanceIn
from ..services.snapshots import record_snapshot

router = APIRouter(tags=["accounts"])


@router.get("/meta")
def meta():
    return {"account_types": ACCOUNT_TYPES, "groups": GROUPS, "categories": CATEGORIES}


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    order = {k: i for i, k in enumerate(ACCOUNT_TYPES)}
    return sorted(db.query(Account).all(), key=lambda a: (order.get(a.type, 99), -abs(a.balance)))


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    account = Account(**body.model_dump())
    db.add(account)
    db.commit()
    record_snapshot(db)
    return account


def _get(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "자산을 찾을 수 없습니다.")
    return account


@router.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, body: AccountIn, db: Session = Depends(get_db)):
    account = _get(db, account_id)
    for k, v in body.model_dump().items():
        setattr(account, k, v)
    db.commit()
    record_snapshot(db)
    return account


@router.patch("/accounts/{account_id}/balance", response_model=AccountOut)
def update_balance(account_id: int, body: BalanceIn, db: Session = Depends(get_db)):
    account = _get(db, account_id)
    account.balance = body.balance
    db.commit()
    record_snapshot(db)
    return account


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = _get(db, account_id)
    db.query(Transaction).filter(Transaction.account_id == account_id).delete()
    db.delete(account)
    db.commit()
    record_snapshot(db)
