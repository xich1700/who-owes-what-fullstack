"""
End-to-end integration test for the Who Owes What API.
Run this against your locally running backend (uvicorn app.main:app --port 8000).

Usage:
    pip install requests
    python test_backend.py

Exits with a non-zero status and prints exactly which check failed,
so any failure is easy to pinpoint and report back.
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8000"
FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print(f"  \u2713 {label}")
    else:
        print(f"  \u2717 {label}  {detail}")
        FAILURES.append(f"{label} {detail}")


def section(title):
    print(f"\n=== {title} ===")


# =========================================================
# 0) Server reachability
# =========================================================
section("Server reachability")
try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    check("Root endpoint responds", r.status_code == 200, r.text)
except requests.exceptions.ConnectionError:
    print("Could not connect to the server at", BASE_URL)
    print("Make sure uvicorn is running: .venv\\Scripts\\uvicorn.exe app.main:app --reload --port 8000")
    sys.exit(1)


# =========================================================
# 1) Auth: signup, login, forgot password
# =========================================================
section("Auth")

unique = str(int(time.time()))
username = f"testuser_{unique}"
password = "test1234"
security_question = "What city were you born in?"
security_answer = "Paris"

r = requests.post(f"{BASE_URL}/auth/signup", json={
    "username": username, "password": password,
    "security_question": security_question, "security_answer": security_answer,
})
check("Signup returns 200", r.status_code == 200, r.text)
token = r.json().get("access_token") if r.status_code == 200 else None
check("Signup returns an access token", bool(token))

r = requests.post(f"{BASE_URL}/auth/signup", json={
    "username": username, "password": password,
    "security_question": security_question, "security_answer": security_answer,
})
check("Duplicate signup is rejected", r.status_code == 400, r.text)

r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": "wrong-password"})
check("Login with wrong password is rejected", r.status_code == 401, r.text)

r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
check("Login with correct password succeeds", r.status_code == 200, r.text)
if r.status_code == 200:
    token = r.json()["access_token"]

HEADERS = {"Authorization": f"Bearer {token}"}

r = requests.post(f"{BASE_URL}/auth/forgot-password/lookup", json={"username": username})
check("Forgot-password lookup finds the account", r.status_code == 200, r.text)
returned_question = r.json().get("security_question") if r.status_code == 200 else None
check("Forgot-password returns the right question", returned_question == security_question)

r = requests.post(f"{BASE_URL}/auth/forgot-password/reset", json={
    "username": username, "security_answer": "wrong answer", "new_password": "irrelevant123",
})
check("Password reset rejects a wrong security answer", r.status_code == 400, r.text)

new_password = "newpass5678"
r = requests.post(f"{BASE_URL}/auth/forgot-password/reset", json={
    "username": username, "security_answer": security_answer, "new_password": new_password,
})
check("Password reset succeeds with the right answer", r.status_code == 200, r.text)

r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": new_password})
check("Can log in with the new password", r.status_code == 200, r.text)
if r.status_code == 200:
    token = r.json()["access_token"]
    HEADERS = {"Authorization": f"Bearer {token}"}

r = requests.get(f"{BASE_URL}/groups")
check("Protected endpoint rejects requests with no token", r.status_code == 401, r.text)


# =========================================================
# 2) Groups and people
# =========================================================
section("Groups and people")

r = requests.post(f"{BASE_URL}/groups", json={"name": "Etretat Weekend", "currency": "EUR"}, headers=HEADERS)
check("Create group succeeds", r.status_code == 200, r.text)
group = r.json()
group_id = group["id"]
check("Group has a share token", bool(group.get("share_token")))
check("Group currency is EUR", group.get("currency") == "EUR")
check("Group starts open (not closed)", group.get("closed") is False)

r = requests.post(f"{BASE_URL}/groups", json={"name": "Etretat Weekend", "currency": "EUR"}, headers=HEADERS)
check("Duplicate group name is rejected", r.status_code == 400, r.text)

r = requests.get(f"{BASE_URL}/groups", headers=HEADERS)
check("List groups includes the new one", any(g["id"] == group_id for g in r.json()))

names = ["Karim", "Lea", "Sam"]
person_ids = {}
for name in names:
    r = requests.post(f"{BASE_URL}/groups/{group_id}/people", json={"name": name}, headers=HEADERS)
    check(f"Add person '{name}'", r.status_code == 200, r.text)
    if r.status_code == 200:
        person_ids[name] = r.json()["id"]

r = requests.post(f"{BASE_URL}/groups/{group_id}/people", json={"name": "karim"}, headers=HEADERS)
check("Duplicate name (case-insensitive) is rejected", r.status_code == 400, r.text)


# =========================================================
# 3) Expenses - equal split and weighted split
# =========================================================
section("Expenses")

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses", json={
    "payer_id": person_ids["Karim"], "amount": 30.0, "label": "Groceries",
    "beneficiary_weights": {person_ids["Karim"]: 1, person_ids["Lea"]: 1, person_ids["Sam"]: 1},
}, headers=HEADERS)
check("Add equal-split expense", r.status_code == 200, r.text)
expense1_id = r.json()["id"] if r.status_code == 200 else None

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses", json={
    "payer_id": person_ids["Lea"], "amount": 20.0, "label": "Restaurant", "is_recurring": True,
    "beneficiary_weights": {person_ids["Lea"]: 0.5, person_ids["Sam"]: 1},
}, headers=HEADERS)
check("Add weighted (uneven) expense", r.status_code == 200, r.text)
expense2_id = r.json()["id"] if r.status_code == 200 else None

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses", json={
    "payer_id": "not-a-real-id", "amount": 10.0, "beneficiary_weights": {person_ids["Karim"]: 1},
}, headers=HEADERS)
check("Expense with an invalid payer is rejected", r.status_code == 400, r.text)

r = requests.get(f"{BASE_URL}/groups/{group_id}/expenses", headers=HEADERS)
check("List expenses returns both", r.status_code == 200 and len(r.json()) == 2, r.text)

if expense2_id:
    r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses/{expense2_id}/repeat", headers=HEADERS)
    check("Repeat a recurring expense", r.status_code == 200, r.text)
    repeated_id = r.json()["id"] if r.status_code == 200 else None

    r = requests.get(f"{BASE_URL}/groups/{group_id}/expenses", headers=HEADERS)
    check("Expense count is now 3 after repeat", r.status_code == 200 and len(r.json()) == 3, r.text)

    if repeated_id:
        r = requests.delete(f"{BASE_URL}/groups/{group_id}/expenses/{repeated_id}", headers=HEADERS)
        check("Delete the repeated expense (cleanup)", r.status_code == 200, r.text)


# =========================================================
# 4) Totals and settlement math
# =========================================================
section("Totals and settlement")

r = requests.get(f"{BASE_URL}/groups/{group_id}/totals", headers=HEADERS)
check("Get totals succeeds", r.status_code == 200, r.text)
totals = r.json() if r.status_code == 200 else {}
check("Total spent is 50.0 (30 + 20)", totals.get("total_spent") == 50.0, totals.get("total_spent"))

balance_sum = round(sum(b["outstanding"] for b in totals.get("balances", [])), 4)
check("Balances sum to exactly zero", balance_sum == 0, balance_sum)

pairs = [(t["from_id"], t["to_id"]) for t in totals.get("settlement_plan", [])]
check("No duplicate transfer pairs in settlement plan", len(pairs) == len(set(pairs)))


# =========================================================
# 5) Repayments
# =========================================================
section("Repayments")

debtor_transfer = next((t for t in totals.get("settlement_plan", [])), None)
if debtor_transfer:
    r = requests.post(f"{BASE_URL}/groups/{group_id}/repayments", json={
        "from_person_id": debtor_transfer["from_id"],
        "to_person_id": debtor_transfer["to_id"],
        "amount": debtor_transfer["amount"],
    }, headers=HEADERS)
    check("Record a repayment matching the suggested transfer", r.status_code == 200, r.text)
    repayment_id = r.json()["id"] if r.status_code == 200 else None

    r = requests.get(f"{BASE_URL}/groups/{group_id}/totals", headers=HEADERS)
    new_totals = r.json()
    new_balance_sum = round(sum(b["outstanding"] for b in new_totals.get("balances", [])), 4)
    check("Balances still sum to zero after repayment", new_balance_sum == 0, new_balance_sum)
    check("Settlement plan shrank after the repayment",
          len(new_totals.get("settlement_plan", [])) <= len(totals.get("settlement_plan", [])))

    if repayment_id:
        r = requests.delete(f"{BASE_URL}/groups/{group_id}/repayments/{repayment_id}", headers=HEADERS)
        check("Undo the repayment (cleanup)", r.status_code == 200, r.text)
else:
    print("  (skipped - no settlement transactions to test against)")


# =========================================================
# 6) People removal rules
# =========================================================
section("People removal rules")

r = requests.delete(f"{BASE_URL}/groups/{group_id}/people/{person_ids['Karim']}", headers=HEADERS)
check("Removing a person who's in an expense is blocked", r.status_code == 400, r.text)

r = requests.post(f"{BASE_URL}/groups/{group_id}/people", json={"name": "Newbie"}, headers=HEADERS)
check("Adding a person to a group with existing expenses works", r.status_code == 200, r.text)
if r.status_code == 200:
    newbie_id = r.json()["id"]
    r = requests.delete(f"{BASE_URL}/groups/{group_id}/people/{newbie_id}", headers=HEADERS)
    check("Removing a person NOT in any expense succeeds", r.status_code == 200, r.text)


# =========================================================
# 7) Natural-language expense parsing
# =========================================================
section("Natural-language parsing")

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses/parse",
                   json={"sentence": "Karim paid \u20ac45 at the restaurant for everyone except Lea"},
                   headers=HEADERS)
check("Parse a valid sentence", r.status_code == 200 and r.json().get("ok") is True, r.text)

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses/parse",
                   json={"sentence": "Marc paid 20 euros for everyone"}, headers=HEADERS)
result = r.json() if r.status_code == 200 else {}
check("Unknown name is rejected, not invented", result.get("ok") is False and "Marc" in (result.get("error") or ""))

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses/parse",
                   json={"sentence": "we paid for the restaurant"}, headers=HEADERS)
result = r.json() if r.status_code == 200 else {}
check("Ambiguous sentence is rejected", result.get("ok") is False)


# =========================================================
# 8) Share link (public, no auth)
# =========================================================
section("Public share link")

share_token = group["share_token"]

r = requests.get(f"{BASE_URL}/share/{share_token}")
check("Share link works with no auth header", r.status_code == 200, r.text)

r = requests.get(f"{BASE_URL}/share/{share_token}/totals")
check("Share link totals endpoint works with no auth", r.status_code == 200, r.text)

r = requests.get(f"{BASE_URL}/share/not-a-real-token")
check("Bogus share token returns 404", r.status_code == 404, r.text)


# =========================================================
# 9) Closing the group
# =========================================================
section("Closing the group")

r = requests.post(f"{BASE_URL}/groups/{group_id}/close", headers=HEADERS)
check("Closing is blocked while balances are non-zero", r.status_code == 400, r.text)

r = requests.get(f"{BASE_URL}/groups/{group_id}/totals", headers=HEADERS)
for t in r.json().get("settlement_plan", []):
    requests.post(f"{BASE_URL}/groups/{group_id}/repayments", json={
        "from_person_id": t["from_id"], "to_person_id": t["to_id"], "amount": t["amount"],
    }, headers=HEADERS)

r = requests.get(f"{BASE_URL}/groups/{group_id}/totals", headers=HEADERS)
final_sum = round(sum(b["outstanding"] for b in r.json().get("balances", [])), 4)
check("Everyone is settled up now", all(abs(b["outstanding"]) < 0.005 for b in r.json().get("balances", [])))

r = requests.post(f"{BASE_URL}/groups/{group_id}/close", headers=HEADERS)
check("Closing succeeds once balances are zero", r.status_code == 200, r.text)

r = requests.post(f"{BASE_URL}/groups/{group_id}/people", json={"name": "TooLate"}, headers=HEADERS)
check("Closed group blocks adding a new person", r.status_code == 400, r.text)

r = requests.post(f"{BASE_URL}/groups/{group_id}/expenses", json={
    "payer_id": person_ids["Karim"], "amount": 5.0, "beneficiary_weights": {person_ids["Karim"]: 1},
}, headers=HEADERS)
check("Closed group blocks adding a new expense", r.status_code == 400, r.text)

r = requests.get(f"{BASE_URL}/share/{share_token}")
check("Closed group is still viewable via the share link", r.status_code == 200 and r.json().get("closed") is True, r.text)


# =========================================================
# 10) Cleanup
# =========================================================
section("Cleanup")

r = requests.delete(f"{BASE_URL}/groups/{group_id}", headers=HEADERS)
check("Delete the test group", r.status_code == 200, r.text)


# =========================================================
# Summary
# =========================================================
print("\n" + "=" * 50)
if FAILURES:
    print(f"{len(FAILURES)} CHECK(S) FAILED:\n")
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
    sys.exit(0)