"""
personality_scorer.py
Sends extracted features to Claude API and gets back structured
personality trait scores + a narrative report.
"""

import json
import anthropic
from typing import Dict


TRAITS = ["Perfectionist", "Hacker", "Academic", "Pragmatist", "Lone Wolf", "Collaborator"]

SYSTEM_PROMPT = """You are an expert software anthropologist. You analyze GitHub repository 
data and infer the personality traits of the developer(s) behind the code.

You will receive a JSON object of extracted features from a repository. 
Based on these features, you MUST return ONLY a valid JSON object — no markdown, no explanation, 
no preamble. Just the raw JSON.

The JSON must follow this exact schema:
{
  "traits": {
    "Perfectionist": <int 0-100>,
    "Hacker": <int 0-100>,
    "Academic": <int 0-100>,
    "Pragmatist": <int 0-100>,
    "Lone Wolf": <int 0-100>,
    "Collaborator": <int 0-100>
  },
  "summary": "<2-3 sentence plain-English personality summary of this developer/team>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "growth_area": "<one specific, constructive growth suggestion>",
  "signature_trait": "<the single most dominant trait name>",
  "evidence": {
    "Perfectionist": "<one specific piece of evidence from the features>",
    "Hacker": "<one specific piece of evidence>",
    "Academic": "<one specific piece of evidence>",
    "Pragmatist": "<one specific piece of evidence>",
    "Lone Wolf": "<one specific piece of evidence>",
    "Collaborator": "<one specific piece of evidence>"
  }
}

Trait scoring guide:
- Perfectionist: high readme_score, conventional commits, low variance in commit length, test files present
- Hacker: short commits, high emoji ratio, low doc ratio, fast iteration (many commits)
- Academic: long readme, many doc files, topic tags, detailed commit messages
- Pragmatist: balanced commit style, config files, practical naming, moderate doc ratio
- Lone Wolf: single contributor, no wiki, few forks, minimal issue refs
- Collaborator: many contributors, issue refs, wiki present, high forks, detailed PRs

Be specific. Reference actual numbers from the features in your evidence.
"""


def score_personality(features: Dict, api_key: str) -> Dict:
    """
    Call Claude API with extracted features and return personality scores.
    
    Args:
        features: Feature dict from feature_extractor + embedder
        api_key: Anthropic API key
    Returns:
        Dict with traits, summary, strengths, growth_area, signature_trait, evidence
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Clean features for the prompt (remove any non-serializable values)
    clean_features = {}
    for k, v in features.items():
        try:
            json.dumps(v)
            clean_features[k] = v
        except (TypeError, ValueError):
            clean_features[k] = str(v)

    user_message = f"""Analyze this GitHub repository and return the personality JSON:

{json.dumps(clean_features, indent=2)}
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return neutral scores with error note
        result = {
            "traits": {t: 50 for t in TRAITS},
            "summary": "Could not parse personality analysis. Please try again.",
            "strengths": ["Unable to determine"],
            "growth_area": "Unable to determine",
            "signature_trait": "Unknown",
            "evidence": {t: "N/A" for t in TRAITS},
            "parse_error": raw[:200],
        }

    return result
