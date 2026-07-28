"""
Rule-based parser for the "quick add via sentence" feature.
Deliberately conservative: never invents a person not already in the
group, and reports specifically what's missing rather than guessing.
"""

import re

AMOUNT_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euros?)?|€\s*(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)
VERB_RE = re.compile(r"\b(paid|spent)\b", re.IGNORECASE)
EXCEPT_RE = re.compile(r"(?:\bfor\s+)?\b(everyone|everybody|all)\b.*?\b(except|but)\b\s+(.+)", re.IGNORECASE)
EVERYONE_RE = re.compile(r"\b(everyone|everybody|all)\b", re.IGNORECASE)
FOR_RE = re.compile(r"\bfor\b\s+(.+)", re.IGNORECASE)


def _normalized(s: str) -> str:
    return s.strip().lower()


def _split_names(fragment: str):
    fragment = re.sub(r"\band\b", ",", fragment, flags=re.IGNORECASE)
    return [n.strip(" .") for n in fragment.split(",") if n.strip(" .")]


def _match_person(name_guess: str, name_by_norm: dict):
    key = _normalized(name_guess)
    if key in name_by_norm:
        return name_by_norm[key]
    for norm_name, pid in name_by_norm.items():
        if norm_name.startswith(key) or key.startswith(norm_name):
            return pid
    return None


def parse_expense_sentence(sentence: str, people: list[dict]) -> dict:
    """
    people: [{"id": str, "name": str}, ...]
    Returns a dict matching ParseExpenseResult - {"ok": True, ...} or
    {"ok": False, "error": "..."}.
    """
    text = sentence.strip()
    if not text:
        return {"ok": False, "error": "Type a sentence first."}

    name_by_norm = {_normalized(p["name"]): p["id"] for p in people}
    all_ids = [p["id"] for p in people]

    verb_match = VERB_RE.search(text)
    if not verb_match:
        return {"ok": False, "error": "I couldn't tell who paid — try including the word 'paid', e.g. \"Karim paid €45 for everyone\"."}

    payer_fragment = text[:verb_match.start()].strip()
    rest = text[verb_match.end():].strip()

    if not payer_fragment:
        return {"ok": False, "error": "I couldn't find who paid — put their name at the start of the sentence."}

    payer_id = _match_person(payer_fragment, name_by_norm)
    if payer_id is None:
        return {"ok": False, "error": f"I don't see '{payer_fragment}' in this group. Add them first, or check the spelling."}

    amount_match = AMOUNT_RE.search(rest)
    if not amount_match:
        return {"ok": False, "error": "I couldn't find an amount — include something like '€45' or '45 euros'."}
    amount_str = (amount_match.group(1) or amount_match.group(2) or "").replace(",", ".")
    try:
        amount = float(amount_str)
    except ValueError:
        amount = None
    if not amount or amount <= 0:
        return {"ok": False, "error": "I couldn't find a valid amount — it needs to be a positive number."}

    beneficiary_ids = None
    except_match = EXCEPT_RE.search(rest)
    if except_match:
        excluded_names = _split_names(except_match.group(3))
        excluded_ids = []
        for n in excluded_names:
            pid = _match_person(n, name_by_norm)
            if pid is None:
                return {"ok": False, "error": f"I don't see '{n}' in this group, so I can't exclude them. Check the spelling."}
            excluded_ids.append(pid)
        beneficiary_ids = [pid for pid in all_ids if pid not in excluded_ids]
    elif EVERYONE_RE.search(rest):
        beneficiary_ids = list(all_ids)
    else:
        for_match = FOR_RE.search(rest)
        if for_match:
            names = _split_names(for_match.group(1))
            found_ids = []
            for n in names:
                pid = _match_person(n, name_by_norm)
                if pid is None:
                    return {"ok": False, "error": f"I don't see '{n}' in this group. Add them first, or check the spelling."}
                found_ids.append(pid)
            if found_ids:
                beneficiary_ids = found_ids

    if not beneficiary_ids:
        return {
            "ok": False,
            "error": "I couldn't tell who this was for — add \"for everyone\", \"for everyone except X\", or list names, e.g. \"for Karim and Léa\"."
        }

    label_zone = rest[amount_match.end():]
    label_zone = EXCEPT_RE.sub("", label_zone)
    label_zone = FOR_RE.sub("", label_zone)
    label = re.sub(r"^(at|on|in|for|the)\b\s*", "", label_zone.strip(), flags=re.IGNORECASE)
    label = re.sub(r"\s*\b(for|at|on|in|the)\b\s*$", "", label, flags=re.IGNORECASE).strip(" .")

    payer_name = next(p["name"] for p in people if p["id"] == payer_id)
    return {
        "ok": True,
        "payer_id": payer_id,
        "payer_name": payer_name,
        "amount": round(amount, 2),
        "label": label,
        "beneficiary_ids": beneficiary_ids,
    }
