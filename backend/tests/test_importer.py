import datetime as dt

from app.schemas import ImportOptions
from app.services import importer
from app.services.categorizer import Categorizer


def test_parse_date_formats():
    assert importer.parse_date("2026.09.01 12:33:10") == dt.date(2026, 9, 1)
    assert importer.parse_date("2026-9-1") == dt.date(2026, 9, 1)
    assert importer.parse_date("20260901") == dt.date(2026, 9, 1)
    assert importer.parse_date("2026년 09월 01일") == dt.date(2026, 9, 1)
    assert importer.parse_date("26.09.01") == dt.date(2026, 9, 1)
    assert importer.parse_date("9/1/2026") == dt.date(2026, 9, 1)
    assert importer.parse_date("46266") == dt.date(2026, 9, 1)  # 엑셀 일련번호
    assert importer.parse_date("합계") is None


def test_parse_amount():
    assert importer.parse_amount("12,300") == 12300
    assert importer.parse_amount("-4,500원") == -4500
    assert importer.parse_amount("(1,000)") == -1000
    assert importer.parse_amount("1000-") == -1000
    assert importer.parse_amount("") is None
    assert importer.parse_amount("abc") is None


def test_categorizer_prefers_longer_keyword_and_direction():
    c = Categorizer()
    assert c.categorize("쿠팡이츠 강남", -1) == "배달"
    assert c.categorize("쿠팡와우 멤버십", -1) == "구독"
    assert c.categorize("쿠팡", -1) == "쇼핑"
    assert c.categorize("쿠팡 환불", 1) == "환급·기타수입"
    assert c.categorize("예금이자", 1) == "이자·배당"
    assert c.categorize("신한카드 대금", -1) == "카드대금"


def test_user_rule_overrides_default():
    c = Categorizer([("스타벅스", "식비")])
    assert c.categorize("스타벅스 역삼점", -1) == "식비"


BANK_CSV = """조회기간,2026.08.01~2026.08.31
계좌번호,123-456-789

거래일시,적요,출금액,입금액,잔액,거래점
2026.08.01 09:10,스타벅스,"4,500",0,"995,500",인터넷
2026.08.01 09:10,스타벅스,"4,500",0,"991,000",인터넷
2026.08.25 10:00,급여,0,"3,000,000","3,991,000",본점
합계,,"9,000","3,000,000",,
"""


def test_bank_csv_split_columns_and_duplicates():
    rows = importer.parse_text(BANK_CSV)
    guess = importer.guess_options(rows)
    assert guess["header_index"] == 3
    assert guess["mode"] == "split"
    assert guess["mapping"].date == 0 and guess["mapping"].description == 1

    opts = ImportOptions(rows=rows, account_id=1, dry_run=True, **guess)
    txs, skipped = importer.convert(opts, Categorizer())
    assert skipped == 1  # 합계 행
    assert [(t["amount"], t["direction"], t["category"]) for t in txs] == [
        (4500, -1, "카페·간식"), (4500, -1, "카페·간식"), (3000000, 1, "급여"),
    ]

    # 이미 한 건이 저장되어 있으면 같은 날 두 번째 결제는 새 거래로 인정한다
    existing = [importer.tx_key(1, dt.date(2026, 8, 1), 4500, -1, "스타벅스")]
    importer.mark_duplicates(txs, existing)
    assert [t["duplicate"] for t in txs] == [True, False, False]


def test_card_statement_positive_is_expense():
    text = "이용일\t이용하신곳\t이용금액\n2026-08-03\t배달의민족\t23000\n2026-08-04\t배달의민족 취소\t-23000\n"
    rows = importer.parse_text(text)
    guess = importer.guess_options(rows)
    assert guess["mode"] == "single"
    # 취소(음수)가 있어 자동 추정은 음수=지출이 되므로 카드 명세서임을 직접 지정
    opts = ImportOptions(rows=rows, account_id=1, **{**guess, "sign": "positive_expense"})
    txs, _ = importer.convert(opts, Categorizer())
    assert [(t["direction"], t["kind"]) for t in txs] == [(-1, "expense"), (1, "income")]
