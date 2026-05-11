"""LLM service for AI-powered rule suggestions.

Supports multiple providers:
- Ollama (local, default)
- OpenAI-compatible APIs (OpenRouter, Apfel, etc.)
"""

import json

import httpx

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
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


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

    category_list = "\n".join(f"- {cat}" for cat in categories)

    return f"""You are a personal finance categorization assistant. Given a list of transaction payees (with optional notes) and available categories, suggest the most appropriate category for each payee. Also suggest the best keyword to use for an automatic matching rule.

Available categories:
{category_list}

Uncategorized payees:
{payee_list}

For each payee, respond with a JSON array where each element has:
- "payee": the exact payee string
- "suggested_category": one of the available categories (must be an exact match)
- "confidence": "high", "medium", or "low"
- "reasoning": brief explanation (1 sentence)
- "match_field": which field the rule should match on — "payee" or "notes"
- "match_value": the keyword or short phrase to use in the rule (e.g. strip branch numbers, transaction IDs, dates, and other noise — keep only the stable merchant/vendor name that would match future transactions)

For match_value: extract the core identifier from the payee or notes. For example, if the payee is "TESCO STORES 4831 LONDON" use "TESCO" or "TESCO STORES". If the notes contain a better identifier than the payee, use match_field "notes" instead.

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

    if provider == "ollama":
        response_text = _suggest_via_ollama(prompt, base_url, model)
    else:
        # OpenRouter, Apfel, and any OpenAI-compatible endpoint
        response_text = _suggest_via_openai(prompt, base_url, model, api_key)

    suggestions = _parse_response(response_text)
    return _validate_suggestions(suggestions, categories)
