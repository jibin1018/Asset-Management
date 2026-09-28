def test_sample_flow(client):
    assert client.post("/api/sample").status_code == 200

    accounts = client.get("/api/accounts").json()
    assert len(accounts) >= 5

    dash = client.get("/api/dashboard").json()
    assert dash["net_worth"]["assets"] > dash["net_worth"]["debts"]
    assert len(dash["monthly"]) == 6
    assert dash["advice"]

    ins = client.get("/api/insights").json()
    names = [s["name"] for s in ins["subscriptions"]]
    assert "넷플릭스" in names
    assert ins["plan"]["allocation"]

    # 카드대금·적금 이체는 지출에서 제외되어야 한다
    month = dash["month"]
    by_cat = client.get("/api/dashboard", params={"month": month}).json()["summary"]["by_category"]
    assert "카드대금" not in by_cat and "저축·투자 이체" not in by_cat


def test_account_and_transaction_crud(client):
    acc = client.post("/api/accounts", json={"name": "테스트 통장", "type": "bank", "balance": 1000000}).json()
    tx = client.post("/api/transactions", json={
        "date": "2026-08-10", "account_id": acc["id"], "amount": 5000, "direction": -1, "description": "스타벅스",
    }).json()
    assert tx["category"] == "카페·간식" and tx["kind"] == "expense"

    patched = client.patch(f"/api/transactions/{tx['id']}", json={"category": "식비"}).json()
    assert patched["category"] == "식비" and patched["manual_category"]

    lst = client.get("/api/transactions", params={"month": "2026-08"}).json()
    assert lst["total"] == 1 and lst["expense"] == 5000

    assert client.delete(f"/api/accounts/{acc['id']}").status_code == 204
    assert client.get("/api/transactions").json()["total"] == 0


def test_import_commit(client):
    acc = client.post("/api/accounts", json={"name": "카드", "type": "card", "balance": 0}).json()
    parsed = client.post("/api/import/paste", json={"text": "이용일,가맹점명,이용금액\n2026-08-03,배달의민족,23000\n"}).json()
    body = {k: parsed[k] for k in ("rows", "header_index", "mapping", "mode", "sign")}
    body |= {"account_id": acc["id"], "dry_run": False}
    first = client.post("/api/import/commit", json=body).json()
    assert first["added"] == 1
    second = client.post("/api/import/commit", json=body).json()
    assert second["added"] == 0 and second["duplicates"] == 1


def test_backup_roundtrip(client):
    client.post("/api/sample")
    data = client.get("/api/backup").json()
    client.post("/api/reset")
    assert client.post("/api/backup/restore", json=data).status_code == 200
    assert client.get("/api/transactions").json()["total"] == len(data["transactions"])
