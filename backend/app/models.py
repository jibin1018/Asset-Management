import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Account(Base):
    """자산 또는 부채 하나 (은행 계좌, 페이 머니, 포인트, 증권 계좌, 카드, 대출 등)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))
    institution: Mapped[str] = mapped_column(String(100), default="")
    # 잔액/평가금액(원). 부채(card, loan)는 갚아야 할 금액을 양수로 저장
    balance: Mapped[int] = mapped_column(Integer, default=0)
    principal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 투자 원금
    interest_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 연 %
    expire_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)  # 포인트 소멸일
    monthly_payment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 적금 납입/대출 상환액
    note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now, onupdate=dt.datetime.now)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # 항상 양수
    direction: Mapped[int] = mapped_column(Integer)  # -1 출금, +1 입금
    description: Mapped[str] = mapped_column(String(300), default="")
    category: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(10))  # expense | income | transfer
    manual_category: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(10), default="manual")  # manual | import | sample
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)


class CategoryRule(Base):
    """사용자 분류 규칙: 거래 내용에 keyword가 포함되면 category로 분류."""

    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))


class Budget(Base):
    __tablename__ = "budgets"

    category: Mapped[str] = mapped_column(String(40), primary_key=True)
    monthly_limit: Mapped[int] = mapped_column(Integer)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    target: Mapped[int] = mapped_column(Integer)
    current: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    # 연결 계좌가 있으면 그 계좌 잔액을 현재 금액으로 사용
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON 인코딩


class NetWorthSnapshot(Base):
    """날짜별 순자산 기록 (자산 잔액이 바뀔 때마다 그날 값을 갱신)."""

    __tablename__ = "net_worth_snapshots"

    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    assets: Mapped[int] = mapped_column(Integer)
    debts: Mapped[int] = mapped_column(Integer)
