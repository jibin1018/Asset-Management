import os
import sys
import tempfile
from pathlib import Path

# 앱을 import하기 전에 테스트용 DB 경로를 지정한다
os.environ["ASSET_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/api/reset")
        yield c
