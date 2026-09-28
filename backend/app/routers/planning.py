import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..constants import CAT_MAP, EXPENSE_CATEGORIES, WANT_CATEGORIES
from ..database import get_db
from ..models import Budget, Goal
from ..schemas import GoalIn, GoalOut
from ..services import analysis

router = APIRouter(tags=["planning"])


# ---------- 예산 ----------
def _budget_rows(db: Session, month: Optional[str]) -> dict:
    ctx = analysis.Ctx(db)
    month = ctx.resolve_month(month)
    spent = ctx.summary(month)["by_category"]
    avg = ctx.averages(month)["by_category"]
    rows = [
        {
            "category": c,
            "bucket": CAT_MAP[c].get("bucket"),
            "limit": ctx.budgets.get(c),
            "spent": spent.get(c, 0),
            "average": avg.get(c, 0),
        }
        for c in EXPENSE_CATEGORIES
    ]
    return {"month": month, "rows": rows}


@router.get("/budgets")
def get_budgets(month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    return _budget_rows(db, month)


@router.put("/budgets")
def set_budgets(body: dict[str, Optional[int]], db: Session = Depends(get_db)):
    """{분류: 월 예산} — 값이 null 또는 0이면 예산 삭제."""
    for category, limit in body.items():
        if category not in EXPENSE_CATEGORIES:
            raise HTTPException(400, f"지출 분류가 아닙니다: {category}")
        if not limit:
            db.query(Budget).filter(Budget.category == category).delete()
        else:
            db.merge(Budget(category=category, monthly_limit=limit))
    db.commit()
    return {"ok": True}


@router.post("/budgets/suggest")
def suggest_budgets(month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    """최근 평균 지출을 기준으로 예산 자동 설정 (선택 지출은 15% 절감 목표)."""
    ctx = analysis.Ctx(db)
    avg = ctx.averages(ctx.resolve_month(month))["by_category"]
    for category, value in avg.items():
        if category not in EXPENSE_CATEGORIES or value <= 0:
            continue
        factor = 0.85 if category in WANT_CATEGORIES else 1.0
        db.merge(Budget(category=category, monthly_limit=max(10000, math.ceil(value * factor / 10000) * 10000)))
    db.commit()
    return _budget_rows(db, month)


# ---------- 목표 ----------
def _goal_out(db: Session, goal: Goal) -> GoalOut:
    return GoalOut(**analysis.goal_status(analysis.Ctx(db), goal))


@router.get("/goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    ctx = analysis.Ctx(db)
    return [GoalOut(**analysis.goal_status(ctx, g)) for g in ctx.goals]


@router.post("/goals", response_model=GoalOut, status_code=201)
def create_goal(body: GoalIn, db: Session = Depends(get_db)):
    goal = Goal(**body.model_dump())
    db.add(goal)
    db.commit()
    return _goal_out(db, goal)


@router.put("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, body: GoalIn, db: Session = Depends(get_db)):
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(404, "목표를 찾을 수 없습니다.")
    for k, v in body.model_dump().items():
        setattr(goal, k, v)
    db.commit()
    return _goal_out(db, goal)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    db.query(Goal).filter(Goal.id == goal_id).delete()
    db.commit()
