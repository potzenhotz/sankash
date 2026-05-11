"""LLM service for AI-powered rule suggestions.

Supports multiple providers:
- Ollama (local, default)
- OpenAI-compatible APIs (OpenRouter, Apfel, etc.)
"""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider: Ollama
# ---------------------------------------------------------------------------


def check_ollama_available(base_url: str) -> bool:
    """Check if Ollama is running and reachable."""
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _suggest_via_ollama(
    prompt: str,
    base_url: str,
    model: str,
) -> str:
    """Send a prompt to Ollama and return the raw response text."""
    resp = httpx.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ---------------------------------------------------------------------------
# Provider: OpenAI-compatible (OpenRouter, Apfel, custom endpoints)
# ---------------------------------------------------------------------------


def check_openai_available(base_url: str, api_key: str | None = None) -> bool:
    """Check if an OpenAI-compatible endpoint is reachable."""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = httpx.get(f"{base_url}/v1/models", headers=headers, timeout=5)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _suggest_via_openai(
    prompt: str,
    base_url: str,
    model: str,
    api_key: str | None = None,
) -> str:
    """Send a prompt to an OpenAI-compatible API and return the response text."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    # OpenRouter recommends these for attribution; harmless for other providers.
    headers.setdefault("HTTP-Referer", "https://github.com/lukasmussle/sankash")
    headers.setdefault("X-Title", "Sankash")

    resp = httpx.post(
        f"{base_url}/v1/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=120,
    )
    if resp.status_code >= 400:
        # Surface the provider's error body — OpenRouter / OpenAI return useful
        # JSON like {"error": {"message": "..."}} that raise_for_status hides.
        detail = ""
        try:
            body = resp.json()
            if isinstance(body, dict) and "error" in body:
                err = body["error"]
                detail = err.get("message", "") if isinstance(err, dict) else str(err)
            if not detail:
                detail = json.dumps(body)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code} from {base_url}: {detail[:500]}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"No choices in response: {json.dumps(data)[:500]}")
    return choices[0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Shared logic
# ---------------------------------------------------------------------------

# Known provider presets
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "ollama": {
        "label": "Ollama (local)",
        "default_base_url": "http://localhost:11434",
        "default_model": "llama3.2",
    },
    "openrouter": {
        "label": "OpenRouter",
        "default_base_url": "https://openrouter.ai/api",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
    },
    "apfel": {
        "label": "Apfel (macOS local)",
        "default_base_url": "http://localhost:11434",
        "default_model": "apple-foundationmodel",
    },
    "openai_compatible": {
        "label": "OpenAI-compatible",
        "default_base_url": "http://localhost:8080",
        "default_model": "",
    },
}


def _build_prompt(
    payees_with_notes: list[dict],
    categories: list[str],
) -> str:
    """Build the categorisation prompt (shared across providers)."""
    payee_list = "\n".join(
        f"- Payee: \"{p['payee']}\""
        + (f" | Sample notes: \"{p['notes_sample']}\"" if p.get("notes_sample") else "")
        for p in payees_with_notes
    )

    category_list = ", ".join(categories)

    return f"""You are a personal finance categorization assistant. Given a list of transactions (payee + notes) and available categories, suggest the best category and the best rule keyword for each one.

Available categories:
{category_list}

Uncategorized transactions:
{payee_list}

For each transaction, respond with a JSON array where each element has:
- "payee": the exact payee string from the input
- "suggested_category": one of the available categories (must be an exact match)
- "confidence": "high", "medium", or "low"
- "reasoning": brief explanation (1 sentence)
- "match_field": "payee" or "notes" — which field a future rule should match on
- "match_value": the short, stable keyword to put in the rule

Choosing match_field — IMPORTANT:
Prefer "notes" by default. Use "notes" in TWO cases:

(a) Payment intermediaries — the payee column is a bank or payment processor like "PAYPAL", "STRIPE", "KLARNA", "VISA DEBIT", "SEPA", "DIRECT DEBIT", "CARD PAYMENT", "GOOGLE PAY", "APPLE PAY". The real merchant is in notes.

(b) Varied-product marketplaces — the payee IS the merchant, but each transaction is a different product that belongs to a different category. This applies to "AMAZON", "AMZN", "AMAZON MKTP", "AMAZON PAYMENTS", "EBAY", "ETSY", "ALIEXPRESS". For these, match on notes with the most descriptive product keyword (e.g. "Reiniger", "Buch", "Kaffee", "Werkzeug") so each Amazon purchase can land in its specific category instead of one catch-all "Shopping" rule. Prefer a German noun if the notes are in German.

Only choose "payee" when the payee is a single-category merchant (e.g. "TESCO STORES", "NETFLIX.COM", "SPOTIFY AB", "REWE", "DM DROGERIE", "SHELL") — places where every purchase reasonably maps to the same category.

Choosing match_value:
Extract the core stable identifier. Strip branch numbers, order IDs, dates, marketplace suffixes ("AMZN Mktp DE", "303-3912143-5240367"), and city names. Examples:
- payee "TESCO STORES 4831 LONDON 20250412" → match_field "payee", match_value "TESCO"
- payee "PAYPAL", notes "PP*NETFLIX.COM SUBSCRIPTION 14.99 EUR" → match_field "notes", match_value "NETFLIX"
- payee "AMAZON", notes "Puly Reiniger für Kaffeemaschinen ... 303-3912... AMZN Mktp DE" → match_field "notes", match_value "Reiniger" (or "Kaffee")

Respond ONLY with the JSON array, no other text."""


def _parse_response(response_text: str) -> list[dict]:
    """Parse an LLM response into a list of suggestion dicts."""
    text = response_text.strip()

    # Strip code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)


def _validate_suggestions(
    suggestions: list[dict],
    categories: list[str],
) -> list[dict]:
    """Ensure suggested categories are from the allowed list."""
    valid: list[dict] = []
    for suggestion in suggestions:
        suggested = suggestion.get("suggested_category", "")
        if suggested in categories:
            valid.append(suggestion)
            continue

        # Case-insensitive fallback
        matched = False
        for cat in categories:
            if cat.lower() == suggested.lower():
                suggestion["suggested_category"] = cat
                valid.append(suggestion)
                matched = True
                break

        if not matched:
            suggestion["confidence"] = "low"
            suggestion["reasoning"] = (
                f"Suggested '{suggested}' not in category list. "
                f"{suggestion.get('reasoning', '')}"
            )
            if categories:
                suggestion["suggested_category"] = categories[0]
                valid.append(suggestion)

    return valid


def check_provider_available(
    provider: str,
    base_url: str,
    api_key: str | None = None,
) -> bool:
    """Check if the configured LLM provider is reachable."""
    if provider == "ollama":
        return check_ollama_available(base_url)
    return check_openai_available(base_url, api_key)


def suggest_categories(
    payees_with_notes: list[dict],
    categories: list[str],
    base_url: str,
    model: str,
    provider: str = "ollama",
    api_key: str | None = None,
) -> list[dict]:
    """
    Use an LLM to suggest categories for uncategorized payees.

    Args:
        payees_with_notes: List of dicts with 'payee' and 'notes_sample' keys.
        categories: List of available category names.
        base_url: Provider API base URL.
        model: Model name/identifier.
        provider: One of 'ollama', 'openrouter', 'apfel', 'openai_compatible'.
        api_key: API key (required for cloud providers like OpenRouter).

    Returns:
        List of dicts with 'payee', 'suggested_category', 'confidence', 'reasoning'.
    """
    prompt = _build_prompt(payees_with_notes, categories)

    print(
        f"\n===== LLM PROMPT [provider={provider} model={model}] =====\n"
        f"{prompt}\n"
        f"===== END PROMPT =====",
        flush=True,
    )

    if provider == "ollama":
        response_text = _suggest_via_ollama(prompt, base_url, model)
    else:
        # OpenRouter, Apfel, and any OpenAI-compatible endpoint
        response_text = _suggest_via_openai(prompt, base_url, model, api_key)

    print(
        f"\n===== LLM RESPONSE [provider={provider}] =====\n"
        f"{response_text}\n"
        f"===== END RESPONSE =====",
        flush=True,
    )

    suggestions = _parse_response(response_text)
    return _validate_suggestions(suggestions, categories)
