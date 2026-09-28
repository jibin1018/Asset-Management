"""은행·카드사·간편결제 거래내역 파일(CSV/XLSX/XLS/붙여넣기)을 거래로 변환.

기관마다 파일 형식이 달라서 다음 순서로 처리한다.
1. 파일을 문자열 2차원 배열(rows)로 읽는다.
2. 머리글 행과 날짜/내용/금액 컬럼을 추정한다. (사용자가 화면에서 수정 가능)
3. 매핑에 따라 거래로 변환하고 기존 거래와 중복을 제거한다.
"""

import csv
import datetime as dt
import io
import re
from collections import Counter
from typing import Optional

import pandas as pd

from ..schemas import ImportMapping, ImportOptions
from .categorizer import Categorizer, kind_of

MAX_ROWS = 20000


# ---------- 파일 읽기 ----------
def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() == "nan" else s


def _frame_to_rows(df: pd.DataFrame) -> list[list[str]]:
    rows = []
    if not isinstance(df.columns, pd.RangeIndex):
        rows.append([_cell(c) for c in df.columns])
    rows.extend([_cell(v) for v in r] for r in df.itertuples(index=False, name=None))
    return rows


def _largest(frames) -> list[list[str]]:
    best: list[list[str]] = []
    for df in frames:
        rows = _frame_to_rows(df)
        if sum(1 for r in rows if any(r)) > sum(1 for r in best if any(r)):
            best = rows
    return best


def parse_text(text: str) -> list[list[str]]:
    text = text.lstrip("﻿")
    sample = "\n".join(text.splitlines()[:30])
    delimiter = max([",", "\t", ";", "|"], key=sample.count)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [[c.strip() for c in row] for row in reader]


def parse_file(file_name: str, data: bytes) -> list[list[str]]:
    name = file_name.lower()
    rows: list[list[str]] = []
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        try:
            sheets = pd.read_excel(io.BytesIO(data), header=None, dtype=str, sheet_name=None)
            rows = _largest(sheets.values())
        except Exception:
            # 국내 은행의 .xls 중 상당수는 실제로 HTML 표 형식이다
            text = _decode(data)
            try:
                rows = _largest(pd.read_html(io.StringIO(text)))
            except Exception:
                rows = parse_text(text)
    else:
        rows = parse_text(_decode(data))
    rows = [r for r in rows if any(c for c in r)]
    return rows[:MAX_ROWS]


# ---------- 값 해석 ----------
def parse_date(value) -> Optional[dt.date]:
    s = _cell(value)
    if not s:
        return None
    candidates = []
    if re.fullmatch(r"\d{5}(\.\d+)?", s):  # 엑셀 날짜 일련번호
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(float(s)))
    m = re.match(r"(\d{4})\s*[.\-/년]?\s*(\d{1,2})\s*[.\-/월]?\s*(\d{1,2})", s)
    if m:
        candidates.append((int(m[1]), int(m[2]), int(m[3])))
    m = re.match(r"(\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})(?!\d)", s)
    if m:
        candidates.append((2000 + int(m[1]), int(m[2]), int(m[3])))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)  # 미국식 m/d/yyyy
    if m:
        candidates.append((int(m[3]), int(m[1]), int(m[2])))
    for y, mo, d in candidates:
        try:
            return dt.date(y, mo, d)
        except ValueError:
            continue
    return None


def parse_amount(value) -> Optional[float]:
    s = _cell(value)
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s.endswith("-"):
        neg, s = True, s[:-1]
    s = re.sub(r"[,\s원₩$]", "", s)
    if s.startswith("-"):
        neg, s = not neg, s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    n = float(s)
    return -n if neg else n


# ---------- 머리글/컬럼 추정 ----------
_DATE_HEADER = re.compile(r"거래\s?일|일시|일자|날짜|이용\s?일|승인\s?일|date", re.I)


def detect_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows[:40]):
        filled = [c for c in row if c]
        if len(filled) >= 3 and any(_DATE_HEADER.search(c) for c in filled):
            return i
    return 0


def _find(header: list[str], patterns: list[str], exclude: Optional[str] = None) -> Optional[int]:
    for pat in patterns:
        for i, h in enumerate(header):
            if re.search(pat, h, re.I) and not (exclude and re.search(exclude, h)):
                return i
    return None


def guess_mapping(header: list[str]) -> ImportMapping:
    m = ImportMapping(
        date=_find(header, [r"거래\s?일시|거래\s?일자|이용\s?일시|승인\s?일시", r"거래\s?일|이용\s?일|승인\s?일|일자|날짜|일시", r"date"]),
        description=_find(header, [r"가맹점|이용처|이용하신\s?곳|상호", r"적요|기재\s?내용|거래\s?내용|내용|거래처|받는\s?분|보낸\s?분|description|merchant"]),
        memo=_find(header, [r"메모|비고|memo"]),
        withdraw=_find(header, [r"출금\s?액|출금\s?금액|찾으신|지급", r"출금|withdraw"], exclude=r"잔액|구분"),
        deposit=_find(header, [r"입금\s?액|입금\s?금액|맡기신", r"입금|deposit"], exclude=r"잔액|구분"),
        amount=_find(header, [r"이용\s?금액|승인\s?금액|결제\s?금액|거래\s?금액", r"금액|amount"], exclude=r"잔액|원금|수수료|할부|포인트"),
    )
    if m.memo is not None and m.memo == m.description:
        m.memo = None
    return m


def guess_options(rows: list[list[str]]) -> dict:
    header_index = detect_header(rows)
    header = rows[header_index] if rows else []
    mapping = guess_mapping(header)
    mode = "split" if mapping.withdraw is not None and mapping.deposit is not None else "single"
    sign = "negative_expense"
    if mode == "single" and mapping.amount is not None:
        values = [parse_amount(_at(r, mapping.amount)) for r in rows[header_index + 1:]]
        # 음수가 하나도 없으면 카드 이용내역처럼 "양수 = 지출"인 파일로 본다
        if not any(v is not None and v < 0 for v in values):
            sign = "positive_expense"
    return {"header_index": header_index, "mapping": mapping, "mode": mode, "sign": sign}


# ---------- 변환 ----------
def _at(row: list[str], idx: Optional[int]) -> str:
    if idx is None or idx < 0 or idx >= len(row):
        return ""
    return row[idx]


def convert(opts: ImportOptions, categorizer: Categorizer) -> tuple[list[dict], int]:
    """(거래 dict 목록, 건너뛴 행 수)를 반환."""
    m = opts.mapping
    out: list[dict] = []
    skipped = 0
    for row in opts.rows[opts.header_index + 1:]:
        if not any(row):
            continue
        date = parse_date(_at(row, m.date))
        if date is None:
            skipped += 1
            continue
        direction, amount = 0, 0.0
        if opts.mode == "split":
            wd = abs(parse_amount(_at(row, m.withdraw)) or 0)
            dp = abs(parse_amount(_at(row, m.deposit)) or 0)
            if wd > 0:
                direction, amount = -1, wd
            elif dp > 0:
                direction, amount = 1, dp
        else:
            v = parse_amount(_at(row, m.amount))
            if v:
                amount = abs(v)
                if opts.sign == "positive_expense":
                    direction = -1 if v > 0 else 1
                else:
                    direction = -1 if v < 0 else 1
        amount_int = int(round(amount))
        if direction == 0 or amount_int <= 0:
            skipped += 1
            continue
        parts = [_at(row, m.description).strip(), _at(row, m.memo).strip()]
        description = " / ".join(p for p in parts if p) or "(내용 없음)"
        category = categorizer.categorize(description, direction)
        out.append({
            "date": date,
            "account_id": opts.account_id,
            "amount": amount_int,
            "direction": direction,
            "description": description[:300],
            "category": category,
            "kind": kind_of(category),
        })
    return out, skipped


def tx_key(account_id: int, date: dt.date, amount: int, direction: int, description: str) -> tuple:
    return (account_id, date, amount, direction, description)


def mark_duplicates(new: list[dict], existing_keys: list[tuple]) -> None:
    """기존 거래와 같은 (계좌, 날짜, 금액, 방향, 내용)을 duplicate=True로 표시.

    같은 날 같은 가게에서 두 번 결제한 경우를 살리기 위해 개수 기준으로 비교한다.
    """
    remaining = Counter(existing_keys)
    for t in new:
        k = tx_key(t["account_id"], t["date"], t["amount"], t["direction"], t["description"])
        if remaining[k] > 0:
            remaining[k] -= 1
            t["duplicate"] = True
        else:
            t["duplicate"] = False
