"""
Pure business logic - no framework dependencies, fully unit-testable.
This is the same tested logic from the Streamlit prototype, carried
over unchanged: weighted expense splitting, balance computation, and
the minimal-transaction settlement algorithm.
"""

import hashlib
import secrets


# ---------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256, salted)
# ---------------------------------------------------------------------
def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), pwd_hash.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, computed = hash_password(password, salt)
    return computed == hash_hex


# ---------------------------------------------------------------------
# Expense splitting (weighted, "largest remainder" method)
# ---------------------------------------------------------------------
def compute_shares(amount: float, beneficiary_weights: dict[str, float]) -> dict[str, float]:
    """
    Splits `amount` among beneficiaries proportionally to their weight
    (weight 1 each = equal split). Works in cents with the largest
    remainder method so shares always sum exactly to the amount,
    regardless of how uneven the weights are.
    """
    cents_total = round(amount * 100)
    total_weight = sum(beneficiary_weights.values())
    if total_weight <= 0:
        beneficiary_weights = {pid: 1 for pid in beneficiary_weights}
        total_weight = len(beneficiary_weights)

    raw = {pid: cents_total * w / total_weight for pid, w in beneficiary_weights.items()}
    base = {pid: int(v) for pid, v in raw.items()}
    remainder = cents_total - sum(base.values())

    order = sorted(beneficiary_weights.keys(), key=lambda pid: (raw[pid] - base[pid]), reverse=True)
    for i in range(remainder):
        base[order[i % len(order)]] += 1

    return {pid: base[pid] / 100 for pid in beneficiary_weights}


def compute_totals(person_ids: list[str], expenses: list[dict], repayments: list[dict]):
    """
    expenses: [{"payer_id": str, "amount": float, "beneficiaries": {person_id: weight}}]
    repayments: [{"from_person_id": str, "to_person_id": str, "amount": float}]

    Returns (paid, share, expense_balance, outstanding_balance, total_spent).
    """
    paid = {pid: 0.0 for pid in person_ids}
    share = {pid: 0.0 for pid in person_ids}
    for exp in expenses:
        paid[exp["payer_id"]] = paid.get(exp["payer_id"], 0.0) + exp["amount"]
        for pid, amt in compute_shares(exp["amount"], exp["beneficiaries"]).items():
            share[pid] = share.get(pid, 0.0) + amt

    expense_balance = {pid: round(paid[pid] - share[pid], 2) for pid in person_ids}

    outstanding = dict(expense_balance)
    for r in repayments:
        outstanding[r["from_person_id"]] = outstanding.get(r["from_person_id"], 0.0) + r["amount"]
        outstanding[r["to_person_id"]] = outstanding.get(r["to_person_id"], 0.0) - r["amount"]
    outstanding = {pid: round(v, 2) for pid, v in outstanding.items()}

    total_spent = sum(paid.values())
    return paid, share, expense_balance, outstanding, total_spent


def simplify_debts(balance: dict[str, float], name_by_id: dict[str, str]):
    """
    Greedy algorithm: turns individual balances into a minimal list of
    "who pays whom" transactions. Never routes through an uninvolved
    third party, never repeats the same pair twice, uses at most
    (n-1) transactions for n people.
    """
    creditors = [[pid, b] for pid, b in balance.items() if b > 0.005]
    debtors = [[pid, -b] for pid, b in balance.items() if b < -0.005]
    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, damt = debtors[i]
        creditor_id, camt = creditors[j]
        amt = round(min(damt, camt), 2)
        transactions.append({
            "from_id": debtor_id, "to_id": creditor_id, "amount": amt,
            "from_name": name_by_id.get(debtor_id, "?"), "to_name": name_by_id.get(creditor_id, "?"),
        })
        debtors[i][1] -= amt
        creditors[j][1] -= amt
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1
    return transactions
