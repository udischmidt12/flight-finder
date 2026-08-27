"""Read the total, currency, date and merchant off a receipt / invoice
image or PDF using Claude vision.

Needs ANTHROPIC_API_KEY (env or .env). One call per receipt, ~1-3 cents.
"""

import base64
import json
import os
import re

import anthropic

MODEL = "claude-opus-5"
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8 MB

PDF_TYPE = "application/pdf"
IMAGE_TYPES = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

_PROMPT = (
    "This file is a single receipt or invoice. Read it and reply with ONLY a "
    "JSON object -- no markdown, no commentary -- with exactly these keys:\n"
    '  "amount": the final total the customer actually paid, as a number with a '
    "dot decimal separator and no currency symbol or thousands separators. Use "
    "the grand total / amount due / balance, never a subtotal or a single line "
    "item. null if you genuinely cannot find it.\n"
    '  "currency": the ISO 4217 code, e.g. "USD", "ILS", "EUR", "THB". Infer it '
    "from currency symbols, the language, or the country when it is not written "
    "out. null if unknown.\n"
    '  "date": the transaction date as "YYYY-MM-DD", or null if not shown.\n'
    '  "merchant": the business name as a short string, or null.\n'
)

_EMPTY = {"amount": None, "currency": None, "date": None, "merchant": None}


class ReceiptError(Exception):
    """Config / size / type / API problem -- surfaced to the user."""


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ReceiptError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


def _source_block(file_bytes, content_type):
    b64 = base64.standard_b64encode(file_bytes).decode("ascii")
    if content_type == PDF_TYPE:
        return {"type": "document",
                "source": {"type": "base64", "media_type": PDF_TYPE, "data": b64}}
    media = IMAGE_TYPES.get(content_type)
    if not media:
        raise ReceiptError(f"unsupported file type: {content_type or 'unknown'}")
    return {"type": "image",
            "source": {"type": "base64", "media_type": media, "data": b64}}


def _coerce(raw):
    """Model's dict -> validated {amount, currency, date, merchant}."""
    amount = raw.get("amount")
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(",", "").strip())
        except ValueError:
            amount = None
    if not isinstance(amount, (int, float)) or amount <= 0:
        amount = None

    currency = raw.get("currency")
    currency = currency.strip().upper() if (
        isinstance(currency, str) and re.fullmatch(r"[A-Za-z]{3}", currency.strip())
    ) else None

    d = raw.get("date")
    d = d.strip() if (
        isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.strip())
    ) else None

    merchant = raw.get("merchant")
    merchant = merchant.strip()[:80] or None if isinstance(merchant, str) else None

    return {"amount": amount, "currency": currency, "date": d, "merchant": merchant}


def scan(file_bytes, content_type):
    """Extract {amount, currency, date, merchant} from a receipt file.

    Returns the dict (amount may be None if the model couldn't find a total).
    Raises ReceiptError for missing key, oversized / unsupported file, or an
    API failure.
    """
    if not file_bytes:
        raise ReceiptError("empty file")
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ReceiptError("file is larger than 8 MB")

    block = _source_block(file_bytes, (content_type or "").lower())
    client = _client()

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=512,
            output_config={"effort": "low"},
            messages=[{"role": "user",
                       "content": [block, {"type": "text", "text": _PROMPT}]}],
        )
    except anthropic.AuthenticationError:
        raise ReceiptError("ANTHROPIC_API_KEY is invalid")
    except anthropic.RateLimitError:
        raise ReceiptError("Claude API rate limit hit -- try again shortly")
    except anthropic.APIStatusError as e:
        raise ReceiptError(f"Claude API error ({e.status_code})")
    except anthropic.APIConnectionError:
        raise ReceiptError("couldn't reach the Claude API")

    text = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return dict(_EMPTY)
    try:
        return _coerce(json.loads(match.group(0)))
    except ValueError:
        return dict(_EMPTY)
