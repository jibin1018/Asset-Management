from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Transaction
from ..schemas import IdsIn, TransactionIn, TransactionList, TransactionOut, TransactionPatch
from ..services.categorizer import build_categorizer, kind_of

router = APIRouter(tags=["transactions"])


@router.get("/months", response_model=list[str])
def months(db: Session = Depends(get_db)):
    rows = db.query(func.strftime("%Y-%m", Transaction.date)).distinct().all()
    return sorted((r[0] for r in rows if r[0]), reverse=True)


@router.get("/transactions", response_model=TransactionList)
def list_transactions(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    account_id: Optional[int] = None,
    category: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(300, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if month:
        query = query.filter(func.strftime("%Y-%m", Transaction.date) == month)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if category:
        query = query.filter(Transaction.category == category)
    if kind:
        query = query.filter(Transaction.kind == kind)
    if q:
        query = query.filter(Transaction.description.contains(q))

    sums = dict(query.with_entities(Transaction.kind, func.sum(Transaction.amount)).group_by(Transaction.kind).all())
    total = query.count()
    items = query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit).all()
    return TransactionList(
        items=[TransactionOut.model_validate(t) for t in items], total=total,
        income=sums.get("income") or 0, expense=sums.get("expense") or 0, transfer=sums.get("transfer") or 0,
    )


@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, db: Session = Depends(get_db)):
    if not db.get(Account, body.account_id):
        raise HTTPException(400, "존재하지 않는 계좌입니다.")
    manual = body.category is not None
    category = body.category or build_categorizer(db).categorize(body.description, body.direction)
    tx = Transaction(
        date=body.date, account_id=body.account_id, amount=body.amount, direction=body.direction,
        description=body.description, category=category, kind=kind_of(category),
        manual_category=manual, source="manual",
    )
    db.add(tx)
    db.commit()
    return tx


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, body: TransactionPatch, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(404, "거래를 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(tx, k, v)
    if data.get("category"):
        tx.kind = kind_of(tx.category)
        tx.manual_category = True
    db.commit()
    return tx


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    db.query(Transaction).filter(Transaction.id == tx_id).delete()
    db.commit()


@router.post("/transactions/bulk-delete")
def bulk_delete(body: IdsIn, db: Session = Depends(get_db)):
    deleted = db.query(Transaction).filter(Transaction.id.in_(body.ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}
