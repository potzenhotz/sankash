"""LLM service for AI-powered rule suggestions using Ollama."""

import json

import httpx


def check_ollama_available(base_url: str) -> bool:
    """Check if Ollama is running and reachable."""
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except httpx.ConnectError:
        return False


def suggest_categories(
    payees_with_notes: list[dict],
    categories: list[str],
    base_url: str,
    model: str,
) -> list[dict]:
    """
    Use a local Ollama model to suggest categories for uncategorized payees.

    Args:
        payees_with_notes: List of dicts with 'payee' and 'notes_sample' keys.
        categories: List of available category names.
        base_url: Ollama API base URL.
        model: Ollama model name.

    Returns:
        List of dicts with 'payee', 'suggested_category', 'confidence', 'reasoning'.
    """
    payee_list = "\n".join(
        f"- Payee: \"{p['payee']}\""
        + (f" | Sample notes: \"{p['notes_sample']}\"" if p.get("notes_sample") else "")
        for p in payees_with_notes
    )

    category_list = "\n".join(f"- {cat}" for cat in categories)

    prompt = f"""You are a personal finance categorization assistant. Given a list of transaction payees and available categories, suggest the most appropriate category for each payee.

Available categories:
{category_list}

Uncategorized payees:
{payee_list}

For each payee, respond with a JSON array where each element has:
- "payee": the exact payee string
- "suggested_category": one of the available categories (must be an exact match)
- "confidence": "high", "medium", or "low"
- "reasoning": brief explanation (1 sentence)

Respond ONLY with the JSON array, no other text."""

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

    response_text = resp.json()["response"].strip()

    # Handle code fences in response
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        response_text = "\n".join(lines)

    suggestions = json.loads(response_text)

    # Validate suggested categories are from the allowed list
    valid_suggestions = []
    for suggestion in suggestions:
        if suggestion.get("suggested_category") in categories:
            valid_suggestions.append(suggestion)
        else:
            # Try case-insensitive match
            matched = False
            for cat in categories:
                if cat.lower() == suggestion.get("suggested_category", "").lower():
                    suggestion["suggested_category"] = cat
                    valid_suggestions.append(suggestion)
                    matched = True
                    break
            if not matched:
                suggestion["confidence"] = "low"
                suggestion["reasoning"] = (
                    f"Suggested '{suggestion.get('suggested_category')}' "
                    f"not in category list. {suggestion.get('reasoning', '')}"
                )
                if categories:
                    suggestion["suggested_category"] = categories[0]
                    valid_suggestions.append(suggestion)

    return valid_suggestions
