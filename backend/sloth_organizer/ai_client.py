"""
LM Studio AI client.

Responsibilities:
- Check whether LM Studio is reachable
- Build a compact file context for the prompt
- Call the local OpenAI-compatible API and parse the JSON plan
- Retry once on malformed JSON; raise on second failure
"""

import json
import re
from typing import Any

from openai import OpenAI

from sloth_organizer.config import settings
from sloth_organizer.models import ScannedFile

# ---------------------------------------------------------------------------
# Connection check
# ---------------------------------------------------------------------------

def check_lm_studio() -> dict[str, Any]:
    """
    Return {"connected": bool, "model": str | None}.
    Tries GET {base_url}/models — succeeds if LM Studio is running.
    """
    try:
        client = _make_client()
        models = client.models.list()
        first_model = models.data[0].id if models.data else None
        return {"connected": True, "model": first_model}
    except Exception:
        return {"connected": False, "model": None}


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_context(files: list[ScannedFile]) -> str:
    """Serialize files as a compact JSON array (no whitespace)."""
    items = []
    for f in files:
        item: dict[str, Any] = {
            "path": f.relative_path,
            "name": f.filename,
            "ext": f.extension,
            "size": f.size_bytes,
            "modified": f.modified_at.isoformat(),
            "mime": f.mime_type,
        }
        if f.content_preview:
            item["preview"] = f.content_preview
        if f.is_duplicate:
            item["duplicate"] = True
        items.append(item)
    return json.dumps(items, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a file organization assistant. Your job is to analyze a list of files \
and produce a concise organization plan.

RULES you must follow:
1. Never delete files. Only move or rename them.
2. Prefer existing folder names if the user already has them.
3. Use a flat structure — maximum one level of subfolders.
4. Preserve file extensions exactly (e.g. report.pdf → Annual_Report.pdf, never Annual_Report).
5. If you are unsure where a file belongs, set destination to "Review".
6. Tasks must be short and actionable (e.g. "Pay October invoice", not a paragraph).
7. Priority must be one of: "high", "medium", "low", or null.
8. Confidence must be a float between 0.0 and 1.0.
9. Return ONLY a valid JSON object — no markdown fences, no prose, no explanation.

OUTPUT SCHEMA (return exactly this structure):
{
  "summary": "<one sentence describing the folder contents>",
  "folders": ["<folder1>", "<folder2>", ...],
  "items": [
    {
      "path": "<original relative path>",
      "destination": "<folder name>",
      "new_name": "<new filename or null>",
      "reason": "<one sentence>",
      "task": "<actionable task or null>",
      "priority": "<high|medium|low|null>",
      "confidence": 0.0
    }
  ]
}
"""


def build_messages(context: str) -> list[dict[str, str]]:
    user_content = (
        "Here are the files to organize:\n\n"
        + context
        + "\n\nReturn the JSON organization plan."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def generate_plan(files: list[ScannedFile]) -> dict[str, Any]:
    """
    Call LM Studio and return the validated plan dict.
    Retries once on parse failure; raises ValueError on second failure.
    """
    context = build_context(files)
    messages = build_messages(context)
    client = _make_client()
    model = settings.LM_STUDIO_MODEL or _detect_model(client)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.2,
            )
            raw = response.choices[0].message.content or ""
            plan = _parse_and_validate(raw)
            return plan
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            # On retry, add a correction nudge
            if attempt == 0:
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your response was not valid JSON. "
                        "Return ONLY the JSON object — no markdown, no explanation."
                    ),
                })

    raise ValueError(
        f"LM Studio returned invalid JSON after 2 attempts. Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_VALID_PRIORITIES = {"high", "medium", "low", None}


def _parse_and_validate(raw: str) -> dict[str, Any]:
    """Extract JSON from the model response and validate its structure."""
    # Strip markdown code fences if the model ignores instructions
    text = _strip_fences(raw).strip()
    plan: dict[str, Any] = json.loads(text)

    if "summary" not in plan or "items" not in plan:
        raise ValueError("Response missing required keys: 'summary' and 'items'")

    if not isinstance(plan["items"], list):
        raise ValueError("'items' must be a list")

    normalized_items = []
    for item in plan["items"]:
        if "path" not in item or "destination" not in item:
            raise ValueError(f"Item missing required keys: {item}")

        # Normalize priority — fold "critical" into "high"
        priority = item.get("priority")
        if priority is not None:
            priority = str(priority).lower()
            if priority == "critical":
                priority = "high"
            if priority not in {"high", "medium", "low"}:
                priority = None

        # Clamp confidence to [0, 1]
        confidence = float(item.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        # Sanitize destination — strip path separators, take only folder name
        destination = str(item["destination"]).replace("/", "").replace("\\", "").strip()
        if not destination:
            destination = "Review"

        normalized_items.append({
            "path": str(item["path"]),
            "destination": destination,
            "new_name": item.get("new_name") or None,
            "reason": str(item.get("reason", "")),
            "task": item.get("task") or None,
            "priority": priority,
            "confidence": confidence,
        })

    plan["items"] = normalized_items
    plan.setdefault("folders", [])
    return plan


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if present."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # If no fences, return as-is (may start with { directly)
    start = text.find("{")
    if start != -1:
        end = text.rfind("}")
        if end != -1:
            return text[start:end + 1]
    return text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_client() -> OpenAI:
    return OpenAI(
        base_url=settings.LM_STUDIO_BASE_URL,
        api_key="lm-studio",          # LM Studio doesn't require a real key
        timeout=120.0,
    )


def _detect_model(client: OpenAI) -> str:
    """Use the first loaded model if LM_STUDIO_MODEL is not set."""
    try:
        models = client.models.list()
        if models.data:
            return models.data[0].id
    except Exception:
        pass
    return "local-model"
