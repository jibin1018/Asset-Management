"""Claude API로 개인화된 재무 조언을 생성 (선택 기능).

개인정보 보호를 위해 원본 거래내역·계좌번호는 보내지 않고,
월별 합계·분류별 합계·자산 유형별 합계·정기 결제 목록 같은 집계값만 보낸다.
"""

import json
import os
from typing import Optional

import anthropic

from ..constants import ACCOUNT_TYPES, GROUPS
from .analysis import Ctx, build_advice, build_plan, recent_months

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM_PROMPT = """당신은 한국에 사는 개인을 돕는 재무 코치입니다.
사용자의 자산·지출 요약 데이터(JSON)를 보고 저축과 지출 절약에 대해 조언합니다.

원칙:
- 데이터에 있는 숫자를 근거로 구체적으로 말합니다. 데이터에 없는 사실은 추측하지 않습니다.
- 가장 효과가 큰 행동 3~5가지를 우선순위대로 제시하고, 각 행동으로 절약·저축할 수 있는 금액을 추정합니다.
- 파킹통장, CMA, 예·적금, 청약, ISA, 연금저축, IRP 같은 한국 금융 제도는 일반적인 특징만 설명하고,
  특정 금융사 상품이나 종목을 추천하지 않습니다. 세제 혜택 한도처럼 바뀔 수 있는 수치는 확인이 필요하다고 알립니다.
- 판단하거나 훈계하지 않고, 실행 가능한 다음 단계로 마무리합니다.
- 한국어 마크다운으로 답하고, 표는 꼭 필요할 때만 씁니다.
"""


class AIUnavailable(Exception):
    pass


def build_context(ctx: Ctx, month: str) -> dict:
    """Claude에게 보낼 집계 데이터. 원본 거래는 포함하지 않는다."""
    nw = ctx.net_worth()
    accounts = [
        {
            "유형": ACCOUNT_TYPES.get(a.type, {}).get("label", a.type),
            "잔액": a.balance,
            **({"연이율%": a.interest_rate} if a.interest_rate is not None else {}),
            **({"투자원금": a.principal} if a.principal else {}),
            **({"소멸예정일": a.expire_date.isoformat()} if a.expire_date else {}),
        }
        for a in ctx.accounts
    ]
    plan = build_plan(ctx, month)
    return {
        "기준월": month,
        "설정": {"목표저축률%": ctx.settings.savings_target_rate, "비상금목표개월": ctx.settings.emergency_months},
        "순자산": {"총자산": nw["assets"], "총부채": nw["debts"], "순자산": nw["net"],
                "유형별": {GROUPS[k]["label"]: v for k, v in nw["by_group"].items()}},
        "자산목록": accounts,
        "월별": [
            {k: ctx.summary(m)[k] for k in ("month", "income", "expense")} | {"분류별지출": ctx.summary(m)["by_category"]}
            for m in recent_months(month, 3)
        ],
        "최근평균": ctx.averages(month),
        "정기결제": [{k: s[k] for k in ("name", "category", "monthly")} for s in ctx.subscriptions()[:15]],
        "예산": ctx.budgets,
        "저축목표": [{k: g[k] for k in ("name", "target", "effective_current", "months_left", "monthly_needed")}
                   for g in plan["goals"]],
        "규칙기반_진단": [f"[{a['level']}] {a['title']}" for a in build_advice(ctx, month)],
    }


async def generate_advice(ctx: Ctx, month: str, question: Optional[str] = None) -> str:
    data = json.dumps(build_context(ctx, month), ensure_ascii=False, default=str)
    ask = question.strip() if question and question.strip() else \
        "이 데이터를 바탕으로 이번 달 지출을 진단하고, 저축 계획과 절약 방법을 조언해 주세요."
    content = f"<financial_summary>\n{data}\n</financial_summary>\n\n{ask}"

    client = anthropic.AsyncAnthropic()
    try:
        response = await client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            # 안전 분류기가 요청을 거절하면 서버가 다른 모델로 자동 재시도
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.AuthenticationError as e:
        raise AIUnavailable("Anthropic API 키가 없거나 올바르지 않습니다. 서버 환경변수 ANTHROPIC_API_KEY를 확인하세요.") from e
    except anthropic.RateLimitError as e:
        raise AIUnavailable("요청이 많아 잠시 제한되었습니다. 잠시 후 다시 시도하세요.") from e
    except anthropic.APIStatusError as e:
        raise AIUnavailable(f"Claude API 오류 ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AIUnavailable("Claude API에 연결하지 못했습니다. 네트워크를 확인하세요.") from e

    if response.stop_reason == "refusal":
        raise AIUnavailable("이 요청에는 답변할 수 없습니다. 질문을 바꿔 다시 시도하세요.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if response.stop_reason == "max_tokens":
        text += "\n\n_(답변이 길어 중간에 잘렸습니다.)_"
    return text


def is_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
