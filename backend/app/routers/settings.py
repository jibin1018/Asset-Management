import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Budget, CategoryRule, Goal, NetWorthSnapshot, Transaction
from ..schemas import RuleCreated, RuleIn, RuleOut, SettingsModel
from ..services.categorizer import build_categorizer, compatible, kind_of
from ..services.sample import clear_all, load_sample
from ..services.settings_store import get_settings, save_settings

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsModel)
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("/settings", response_model=SettingsModel)
def write_settings(body: SettingsModel, db: Session = Depends(get_db)):
    return save_settings(db, body)


# ---------- 분류 규칙 ----------
@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(CategoryRule).order_by(CategoryRule.id.desc()).all()


@router.post("/rules", response_model=RuleCreated, status_code=201)
def create_rule(body: RuleIn, db: Session = Depends(get_db)):
    keyword = body.keyword.strip()
    rule = db.query(CategoryRule).filter(CategoryRule.keyword == keyword).first()
    if rule:
        rule.category = body.category
    else:
        rule = CategoryRule(keyword=keyword, category=body.category)
        db.add(rule)
    updated = 0
    if body.apply:
        needle = keyword.upper()
        for tx in db.query(Transaction).all():
            if needle in tx.description.upper() and compatible(body.category, tx.direction) \
                    and tx.category != body.category:
                tx.category = body.category
                tx.kind = kind_of(body.category)
                tx.manual_category = True
                updated += 1
    db.commit()
    return RuleCreated(rule=RuleOut.model_validate(rule), updated=updated)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    db.query(CategoryRule).filter(CategoryRule.id == rule_id).delete()
    db.commit()


@router.post("/rules/reapply")
def reapply_rules(db: Session = Depends(get_db)):
    """직접 분류를 바꾸지 않은 모든 거래를 현재 규칙으로 다시 분류."""
    cat = build_categorizer(db)
    updated = 0
    for tx in db.query(Transaction).filter(Transaction.manual_category.is_(False)).all():
        new = cat.categorize(tx.description, tx.direction)
        if new != tx.category:
            tx.category, tx.kind = new, kind_of(new)
            updated += 1
    db.commit()
    return {"updated": updated}


# ---------- 데이터 관리 ----------
def _rows(db: Session, model) -> list[dict]:
    cols = [c.name for c in model.__table__.columns]
    out = []
    for obj in db.query(model).all():
        row = {}
        for c in cols:
            v = getattr(obj, c)
            row[c] = v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v
        out.append(row)
    return out


BACKUP_MODELS = [("accounts", Account), ("transactions", Transaction), ("rules", CategoryRule),
                 ("budgets", Budget), ("goals", Goal), ("snapshots", NetWorthSnapshot)]


@router.get("/backup")
def backup(db: Session = Depends(get_db)):
    data = {name: _rows(db, model) for name, model in BACKUP_MODELS}
    data["settings"] = get_settings(db).model_dump()
    data["version"] = 1
    data["exported_at"] = dt.datetime.now().isoformat(timespec="seconds")
    return data


def _restore_value(column, value):
    if value is None:
        return None
    py = column.type.python_type
    if py is dt.datetime:
        return dt.datetime.fromisoformat(value)
    if py is dt.date:
        return dt.date.fromisoformat(value)
    return value


@router.post("/backup/restore")
def restore(body: dict, db: Session = Depends(get_db)):
    if body.get("version") != 1:
        raise HTTPException(400, "지원하지 않는 백업 파일입니다.")
    try:
        clear_all(db, commit=False)  # 복원이 실패하면 롤백으로 기존 데이터를 되살린다
        for name, model in BACKUP_MODELS:  # 계좌를 먼저 넣어야 외래키가 맞는다
            columns = {c.name: c for c in model.__table__.columns}
            for row in body.get(name, []):
                db.add(model(**{k: _restore_value(columns[k], v) for k, v in row.items() if k in columns}))
            db.flush()
        save_settings(db, SettingsModel(**body.get("settings", {})))  # 여기서 한 번에 커밋
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"복원에 실패했습니다: {e}") from e
    return {"ok": True}


@router.post("/sample")
def sample(db: Session = Depends(get_db)):
    load_sample(db)
    return {"ok": True}


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    clear_all(db)
    return {"ok": True}
