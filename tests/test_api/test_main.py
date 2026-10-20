"""Tests for the JSON API."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from sankash.api.main import app, get_data_dir
from sankash.core.models import Account, Category, Transaction
from sankash.services import account_service, category_service, transaction_service


@pytest.fixture
def client(test_data_dir: str) -> TestClient:
    app.dependency_overrides[get_data_dir] = lambda: test_data_dir
    account_service.create_account(test_data_dir, Account(name="Giro", bank="Bank"))
    category_service.create_category(test_data_dir, Category(name="Lebensmittel"))
    category_service.create_category(
        test_data_dir, Category(name="Supermarkt", parent_category="Lebensmittel")
    )
    transaction_service.create_transaction(
        test_data_dir,
        Transaction(
            account_id=1,
            date=date(2024, 1, 2),
            payee="REWE Markt",
            notes="Kartenzahlung",
            amount=-42.0,
        ),
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_transactions_and_categories(client: TestClient) -> None:
    txns = client.get("/api/transactions").json()
    assert txns[0]["payee"] == "REWE Markt"
    assert txns[0]["account_name"] == "Giro"
    assert txns[0]["category"] is None and txns[0]["category_source"] is None

    cats = client.get("/api/categories").json()
    assert [c["display"] for c in cats] == ["Lebensmittel", "Lebensmittel > Supermarkt"]


def test_rule_then_manual_then_reset(client: TestClient) -> None:
    r = client.post(
        "/api/rules/conditions",
        json={"category": "Supermarkt", "field": "payee", "value": " rewe "},
    )
    assert r.status_code == 204
    txn = client.get("/api/transactions").json()[0]
    assert (txn["category"], txn["category_source"]) == ("Supermarkt", "rule")

    assert (
        client.put("/api/transactions/1/category", json={"category": "Lebensmittel"}).status_code
        == 204
    )
    txn = client.get("/api/transactions").json()[0]
    assert (txn["category"], txn["category_source"]) == ("Lebensmittel", "manual")

    assert client.delete("/api/transactions/1/category").status_code == 204
    assert client.get("/api/transactions").json()[0]["category_source"] == "rule"


def test_rejects_bad_input(client: TestClient) -> None:
    assert client.put("/api/transactions/1/category", json={"category": "Nope"}).status_code == 400
    assert (
        client.put("/api/transactions/99/category", json={"category": "Supermarkt"}).status_code
        == 404
    )
    bad_field = {"category": "Supermarkt", "field": "amount", "value": "x"}
    assert client.post("/api/rules/conditions", json=bad_field).status_code == 422
    blank = {"category": "Supermarkt", "field": "payee", "value": "   "}
    assert client.post("/api/rules/conditions", json=blank).status_code == 422
