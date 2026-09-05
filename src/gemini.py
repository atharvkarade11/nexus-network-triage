import json
import os

from google import genai
from google.genai import types


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    return genai.Client(api_key=api_key)


def analyze_incident(incident, runbooks):
    evidence = []

    for runbook in runbooks:
        evidence.append({
            "runbook_id": runbook["runbook_id"],
            "title": runbook["title"],
            "source": runbook["source"],
            "content": runbook["content"]
        })

    prompt = f"""
You are NEXUS, an intelligent network incident triage assistant.

Use ONLY the incident data and runbook evidence provided below.

Do not invent causes, commands, troubleshooting steps, or facts.

If the evidence is insufficient or the incident family is unknown,
set escalation_required to true.

INCIDENT:
{json.dumps(incident, indent=2)}

RUNBOOK EVIDENCE:
{json.dumps(evidence, indent=2)}

Return ONLY valid JSON with exactly these keys:

{{
    "summary": "...",
    "probable_cause": "...",
    "recommended_actions": [
        "...",
        "..."
    ],
    "confidence": "high|medium|low",
    "escalation_required": true,
    "escalation_reason": "...",
    "evidence": [
        {{
            "runbook_id": "...",
            "source": "...",
            "claim": "..."
        }}
    ]
}}
"""

    client = get_client()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)