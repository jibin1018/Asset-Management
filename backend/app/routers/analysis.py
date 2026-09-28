from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AIAdviceIn, AIAdviceOut
from ..services import ai_advisor, analysis

router = APIRouter(tags=["analysis"])

MonthQuery = Query(None, pattern=r"^\d{4}-\d{2}$")


@router.get("/dashboard")
def dashboard(month: Optional[str] = MonthQuery, db: Session = Depends(get_db)):
    ctx = analysis.Ctx(db)
    return analysis.dashboard(ctx, ctx.resolve_month(month))


@router.get("/insights")
def insights(month: Optional[str] = MonthQuery, db: Session = Depends(get_db)):
    ctx = analysis.Ctx(db)
    return analysis.insights(ctx, ctx.resolve_month(month))


@router.get("/insights/ai/status")
def ai_status():
    return {"configured": ai_advisor.is_configured(), "model": ai_advisor.MODEL}


@router.post("/insights/ai", response_model=AIAdviceOut)
async def ai_advice(body: AIAdviceIn, db: Session = Depends(get_db)):
    ctx = analysis.Ctx(db)
    if not ctx.txs and not ctx.accounts:
        raise HTTPException(400, "분석할 데이터가 없습니다. 자산과 거래내역을 먼저 등록하세요.")
    try:
        text = await ai_advisor.generate_advice(ctx, ctx.resolve_month(body.month), body.question)
    except ai_advisor.AIUnavailable as e:
        raise HTTPException(503, str(e)) from e
    return AIAdviceOut(text=text, model=ai_advisor.MODEL)
