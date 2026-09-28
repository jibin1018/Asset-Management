from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Transaction
from ..schemas import ImportOptions, ImportPreviewRow, ImportResult, ParsedFile, PasteIn
from ..services import importer
from ..services.categorizer import build_categorizer

router = APIRouter(prefix="/import", tags=["import"])

MAX_UPLOAD = 20 * 1024 * 1024


def _parsed(file_name: str, rows: list[list[str]]) -> ParsedFile:
    if not rows:
        raise HTTPException(400, "파일에서 표 데이터를 찾지 못했습니다.")
    return ParsedFile(file_name=file_name, rows=rows, **importer.guess_options(rows))


@router.post("/parse", response_model=ParsedFile)
async def parse_upload(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "파일이 너무 큽니다 (최대 20MB).")
    try:
        rows = importer.parse_file(file.filename or "upload.csv", data)
    except Exception as e:  # 손상된 파일, 암호 걸린 엑셀 등
        raise HTTPException(400, f"파일을 읽지 못했습니다: {e}") from e
    return _parsed(file.filename or "upload", rows)


@router.post("/paste", response_model=ParsedFile)
def parse_paste(body: PasteIn):
    return _parsed("붙여넣기", importer.parse_text(body.text))


@router.post("/commit", response_model=ImportResult)
def commit(opts: ImportOptions, db: Session = Depends(get_db)):
    """dry_run=True면 미리보기만, False면 중복을 제외하고 저장."""
    if not db.get(Account, opts.account_id):
        raise HTTPException(400, "가져올 계좌를 선택하세요.")
    m = opts.mapping
    if m.date is None:
        raise HTTPException(400, "날짜 컬럼을 지정하세요.")
    if opts.mode == "split" and m.withdraw is None and m.deposit is None:
        raise HTTPException(400, "출금 또는 입금 컬럼을 지정하세요.")
    if opts.mode == "single" and m.amount is None:
        raise HTTPException(400, "금액 컬럼을 지정하세요.")

    new, skipped = importer.convert(opts, build_categorizer(db))
    existing = db.query(
        Transaction.account_id, Transaction.date, Transaction.amount, Transaction.direction, Transaction.description
    ).filter(Transaction.account_id == opts.account_id).all()
    importer.mark_duplicates(new, [importer.tx_key(*row) for row in existing])

    fresh = [t for t in new if not t["duplicate"]]
    if not opts.dry_run:
        db.add_all(Transaction(**{k: v for k, v in t.items() if k != "duplicate"}, source="import") for t in fresh)
        db.commit()

    return ImportResult(
        total=len(new),
        added=0 if opts.dry_run else len(fresh),
        duplicates=len(new) - len(fresh),
        skipped=skipped,
        preview=[ImportPreviewRow(**{k: t[k] for k in ImportPreviewRow.model_fields}) for t in new[:30]],
    )
