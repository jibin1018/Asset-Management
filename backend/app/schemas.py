import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import ACCOUNT_TYPES, CAT_MAP


def _check_category(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in CAT_MAP:
        raise ValueError(f"알 수 없는 분류입니다: {v}")
    return v


# ---------- 자산 ----------
class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str
    institution: str = ""
    balance: int = 0
    principal: Optional[int] = None
    interest_rate: Optional[float] = None
    expire_date: Optional[dt.date] = None
    monthly_payment: Optional[int] = None
    note: str = ""

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in ACCOUNT_TYPES:
            raise ValueError(f"알 수 없는 자산 유형입니다: {v}")
        return v


class AccountOut(AccountIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    updated_at: dt.datetime


class BalanceIn(BaseModel):
    balance: int


# ---------- 거래 ----------
class TransactionIn(BaseModel):
    date: dt.date
    account_id: int
    amount: int = Field(gt=0)
    direction: Literal[-1, 1]
    description: str = ""
    category: Optional[str] = None  # 비우면 자동 분류

    @field_validator("category")
    @classmethod
    def check_category(cls, v: Optional[str]) -> Optional[str]:
        return _check_category(v)


class TransactionPatch(BaseModel):
    date: Optional[dt.date] = None
    amount: Optional[int] = Field(default=None, gt=0)
    direction: Optional[Literal[-1, 1]] = None
    description: Optional[str] = None
    category: Optional[str] = None

    @field_validator("category")
    @classmethod
    def check_category(cls, v: Optional[str]) -> Optional[str]:
        return _check_category(v)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: dt.date
    account_id: int
    amount: int
    direction: int
    description: str
    category: str
    kind: str
    manual_category: bool
    source: str


class TransactionList(BaseModel):
    items: list[TransactionOut]
    total: int
    income: int
    expense: int
    transfer: int


class IdsIn(BaseModel):
    ids: list[int]


# ---------- 가져오기 ----------
class ImportMapping(BaseModel):
    date: Optional[int] = None
    description: Optional[int] = None
    memo: Optional[int] = None
    amount: Optional[int] = None
    withdraw: Optional[int] = None
    deposit: Optional[int] = None


class ParsedFile(BaseModel):
    file_name: str
    rows: list[list[str]]
    header_index: int
    mapping: ImportMapping
    mode: Literal["split", "single"]
    sign: Literal["negative_expense", "positive_expense"]


class PasteIn(BaseModel):
    text: str


class ImportOptions(BaseModel):
    rows: list[list[str]]
    header_index: int = 0
    mapping: ImportMapping
    mode: Literal["split", "single"] = "split"
    sign: Literal["negative_expense", "positive_expense"] = "negative_expense"
    account_id: int
    dry_run: bool = True


class ImportPreviewRow(BaseModel):
    date: dt.date
    amount: int
    direction: int
    description: str
    category: str
    kind: str
    duplicate: bool


class ImportResult(BaseModel):
    total: int
    added: int
    duplicates: int
    skipped: int
    preview: list[ImportPreviewRow]


# ---------- 규칙 / 예산 / 목표 / 설정 ----------
class RuleIn(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    category: str
    apply: bool = True  # 기존 거래에도 적용

    @field_validator("category")
    @classmethod
    def check_category(cls, v: Optional[str]) -> Optional[str]:
        return _check_category(v)


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    keyword: str
    category: str


class RuleCreated(BaseModel):
    rule: RuleOut
    updated: int


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target: int = Field(gt=0)
    current: int = 0
    deadline: Optional[dt.date] = None
    account_id: Optional[int] = None


class GoalOut(GoalIn):
    id: int
    effective_current: int
    progress: float
    months_left: Optional[int]
    monthly_needed: Optional[int]


class SettingsModel(BaseModel):
    savings_target_rate: float = Field(default=20, ge=0, le=90)  # 수입 대비 목표 저축률 %
    emergency_months: float = Field(default=6, ge=0, le=36)  # 비상금 목표 (월 지출 x N)
    monthly_income: int = Field(default=0, ge=0)  # 수입 내역이 없을 때 사용할 월 수입


class AIAdviceIn(BaseModel):
    month: Optional[str] = None
    question: Optional[str] = Field(default=None, max_length=2000)


class AIAdviceOut(BaseModel):
    text: str
    model: str
