"""Travel expense storage + currency conversion."""

import json
import os
import time
import uuid

import requests

EXPENSES_PATH = os.path.join(os.path.dirname(__file__), "expenses.json")
CURRENCY_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{}.json"
TARGET_CURRENCY = "ils"

CATEGORIES = ["Food", "Transport", "Lodging", "Activities", "Shopping", "Other"]


def load_expenses():
    if not os.path.exists(EXPENSES_PATH):
        return []
    with open(EXPENSES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_expenses(expenses):
    with open(EXPENSES_PATH, "w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2, ensure_ascii=False)


def convert_to_ils(amount, currency):
    """Convert amount (in `currency`) to ILS. Returns None if the lookup
    fails -- the expense still gets saved with its original amount, just
    without a converted total."""
    currency = currency.lower()
    if currency == TARGET_CURRENCY:
        return round(amount, 2)

    try:
        resp = requests.get(CURRENCY_API_URL.format(currency), timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    data = resp.json()
    rate = data.get(currency, {}).get(TARGET_CURRENCY)
    if rate is None:
        return None
    return round(amount * rate, 2)


def add_expense(country, category, amount, currency, expense_date, note):
    expenses = load_expenses()
    record = {
        "id": uuid.uuid4().hex,
        "country": country,
        "category": category,
        "amount": amount,
        "currency": currency.upper(),
        "amount_ils": convert_to_ils(amount, currency),
        "date": expense_date,
        "note": note,
        "logged_at": time.time(),
    }
    expenses.append(record)
    save_expenses(expenses)
    return record


def update_expense(expense_id, country, category, amount, currency, expense_date, note):
    expenses = load_expenses()
    for e in expenses:
        if e["id"] == expense_id:
            e["country"] = country
            e["category"] = category
            e["amount"] = amount
            e["currency"] = currency.upper()
            e["amount_ils"] = convert_to_ils(amount, currency)
            e["date"] = expense_date
            e["note"] = note
            save_expenses(expenses)
            return e
    return None


def delete_expense(expense_id):
    expenses = load_expenses()
    remaining = [e for e in expenses if e["id"] != expense_id]
    if len(remaining) == len(expenses):
        return False
    save_expenses(remaining)
    return True


def summarize(expenses):
    total_ils = 0.0
    by_category = {}
    by_country = {}
    unconverted = 0

    for e in expenses:
        amount_ils = e.get("amount_ils")
        if amount_ils is None:
            unconverted += 1
            continue
        total_ils += amount_ils
        by_category[e["category"]] = by_category.get(e["category"], 0) + amount_ils
        by_country[e["country"]] = by_country.get(e["country"], 0) + amount_ils

    return {
        "total_ils": round(total_ils, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "by_country": {k: round(v, 2) for k, v in by_country.items()},
        "unconverted_count": unconverted,
    }
