"""Tests for ai_client validation logic."""
import json
from sloth_organizer.ai_client import _parse_and_validate

CLEAN = json.dumps({
    "summary": "Mix of invoices and proposals.",
    "folders": ["Finance", "Projects"],
    "items": [
        {
            "path": "invoice_oct.pdf",
            "destination": "Finance",
            "new_name": "Invoice_October_2026.pdf",
            "reason": "Looks like an invoice.",
            "task": "Pay October invoice",
            "priority": "high",
            "confidence": 0.91,
        },
        {
            "path": "project-proposal-v7.pdf",
            "destination": "Projects",
            "new_name": None,
            "reason": "Project proposal document.",
            "task": None,
            "priority": None,
            "confidence": 0.94,
        },
    ],
})

FENCED = "```json\n" + CLEAN + "\n```"

CRITICAL = json.dumps({
    "summary": "s", "folders": [],
    "items": [{"path": "x.pdf", "destination": "Finance", "new_name": None,
               "reason": "r", "task": "t", "priority": "critical", "confidence": 0.9}],
})

CLAMPED = json.dumps({
    "summary": "s", "folders": [],
    "items": [{"path": "x.pdf", "destination": "Finance", "new_name": None,
               "reason": "r", "task": None, "priority": None, "confidence": 1.8}],
})

p1 = _parse_and_validate(CLEAN)
assert p1["summary"] == "Mix of invoices and proposals."
assert p1["items"][0]["priority"] == "high"
assert p1["items"][1]["task"] is None
print("Test 1 (clean JSON): OK")

p2 = _parse_and_validate(FENCED)
assert p2["items"][0]["path"] == "invoice_oct.pdf"
print("Test 2 (markdown fence): OK")

p3 = _parse_and_validate(CRITICAL)
assert p3["items"][0]["priority"] == "high"
print("Test 3 (critical->high): OK")

p4 = _parse_and_validate(CLAMPED)
assert p4["items"][0]["confidence"] == 1.0
print("Test 4 (confidence clamped): OK")

print("\nAll validation tests passed.")
