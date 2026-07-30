"""
Receipt scanning - optional, needs the caller's own Anthropic API key.
The key is only ever used for the single request; it's never written
to disk or the database. Never creates an expense directly - the
caller (frontend) always routes the result through the normal
add-expense confirmation screen.
"""

import base64
import json
import re


def extract_receipt_via_ai(image_bytes: bytes, media_type: str, api_key: str):
    """
    Returns (result_dict, error_message). result_dict has "amount" and
    "label" when the model could read the receipt.
    """
    try:
        import anthropic
    except ImportError:
        return None, "This feature needs the 'anthropic' package. Run: pip install anthropic"

    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_data}},
                    {"type": "text", "text": (
                        "This is a photo of a receipt. Reply with ONLY compact JSON, no markdown fences, "
                        "no explanation: {\"amount\": <total amount as a plain number, or null if unreadable>, "
                        "\"label\": \"<short merchant or item description, or empty string if unreadable>\"}"
                    )},
                ],
            }],
        )
    except Exception as e:
        return None, f"Couldn't reach the AI service: {e}"

    raw_text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text").strip()
    raw_text = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw_text)
    except (ValueError, TypeError):
        return None, "The AI's response wasn't valid data. Try a clearer photo, or enter the expense manually."

    amount = parsed.get("amount")
    label = (parsed.get("label") or "").strip()

    if amount is None:
        return None, "Couldn't read a total on this receipt. Try a clearer photo, or enter the expense manually."
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        return None, "Couldn't read a valid total on this receipt. Try a clearer photo, or enter it manually."
    if amount <= 0:
        return None, "That receipt's total didn't come out positive. Try a clearer photo, or enter it manually."

    return {"amount": amount, "label": label}, None
