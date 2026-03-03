"""
AI-Generated Report Cards for Module Training Sessions.

Unlike full call simulations (which use the deterministic GradingEngine),
module sessions are voice-coached lessons. The report card here is generated
entirely by the LLM based on the conversation transcript — what the student
practiced, how they performed, what the coach observed, and what to work on.

This produces a structured report with:
- Overall performance summary
- Strengths observed during the session
- Areas that need improvement
- Specific homework / practice assignments
- Key moments from the session
"""

from __future__ import annotations

import json
import logging
import os

import re

import openai

logger = logging.getLogger(__name__)

# Regex to clean stutter artifacts: 3+ consecutive repeated words
_STUTTER_RE = re.compile(r'\b(\w+)(?:\s*,?\s+\1){2,}\b', re.IGNORECASE)


def _clean_transcript_text(text: str) -> str:
    """Remove stutter artifacts from transcript text before grading."""
    return _STUTTER_RE.sub(lambda m: m.group(1), text).strip()


_MODULE_REPORT_PROMPT = """You are an elite sales training analyst reviewing a completed training module session.
You have access to the full conversation transcript between the AI coach and the student.

## YOUR TASK

Analyze this training session and produce a structured report card. Be specific about
what happened in THIS session — reference actual quotes, moments, and observations.

## CRITICAL: TRANSCRIPT QUALITY NOTICE

This transcript was captured via real-time voice-to-text during a live coaching session.
The audio pipeline may introduce artifacts that do NOT reflect the student's actual speech:

- **Repeated words** (e.g., "my my my name") are often caused by audio echo or
  transcription overlap, NOT the student actually stuttering. Do NOT penalize the student
  for repeated words unless the coach explicitly addressed stuttering as a coaching point.
- **Truncated sentences** ending in "..." may be partial transcriptions, not the student
  trailing off.
- **Slight word variations** between similar entries may be the same utterance transcribed
  at different points.

**Your job is to evaluate the student's SALES SKILLS — their pitch, objection handling,
rapport building, and technique. Ignore transcription quality artifacts entirely.**

## SESSION INFO

**Module:** {module_name}
**Module Key:** {module_key}
**Duration:** {duration_seconds} seconds
**Total Turns:** {total_turns} (Student: {student_turns}, Coach: {coach_turns})
**Session Status:** {session_status}

## CONVERSATION TRANSCRIPT

{transcript}

## WHAT TO GENERATE

Return a JSON object with this exact structure. Every field must contain specific,
actionable analysis based on what actually happened in the transcript above.

```json
{{
  "overall_score": <number 0-100, based on student engagement, effort, and skill demonstration>,
  "overall_grade": "<A/B/C/D/F letter grade>",
  "summary": "<2-3 sentence overview of the session — what was covered and how the student performed>",
  "strengths": [
    {{
      "skill": "<specific skill demonstrated>",
      "observation": "<what they did well, with a quote or specific moment from the session>",
      "impact": "<why this matters for their sales career>"
    }}
  ],
  "areas_for_improvement": [
    {{
      "skill": "<specific skill that needs work>",
      "observation": "<what happened — quote their words or describe the moment>",
      "coaching": "<specific, actionable advice on how to improve this>",
      "drill": "<a concrete exercise they can do to practice this skill>"
    }}
  ],
  "key_moments": [
    "<Brief description of a notable moment from the session — a breakthrough, a struggle, a turning point>"
  ],
  "homework": [
    {{
      "title": "<short exercise name>",
      "description": "<what to practice and how>",
      "success_criteria": "<how they know they've done it right>",
      "estimated_time": "<e.g., '5 minutes', '10 minutes'>"
    }}
  ],
  "coach_notes": "<1-2 sentences of overall coaching direction — what should they focus on NEXT session>"
}}
```

## GRADING GUIDELINES

- **A (85-100):** Student showed strong engagement, nailed most drills, demonstrated clear improvement during the session, and applied feedback immediately.
- **B (70-84):** Student was engaged and made good effort. Got some things right, struggled with others, but showed willingness to improve.
- **C (55-69):** Student participated but struggled with core concepts. Needs more practice on fundamentals before advancing.
- **D (40-54):** Student showed minimal engagement or significant struggles with basic concepts. May need to repeat this module.
- **F (0-39):** Student barely participated, refused to practice, or showed no improvement despite coaching.

Be HONEST but ENCOURAGING. The goal is to help them improve, not discourage them.
If the session was short or ended early, note that in the summary and adjust the score accordingly.
Include 2-4 strengths, 2-4 areas for improvement, 2-4 key moments, and 2-4 homework items.

Return ONLY the JSON — no markdown fences, no explanation."""


async def generate_module_report_card(
    module_key: str,
    module_name: str,
    conversation_log: list[dict],
    duration_seconds: int,
    student_turns: int,
    coach_turns: int,
    session_qualified: bool,
) -> dict | None:
    """Generate an AI-powered report card for a module training session.

    Returns the report dict on success, or None if generation fails.
    Falls back gracefully — module sessions still work without report cards.
    """
    api_key = os.getenv("XAI_API_KEY", "")
    if not api_key:
        logger.warning("No XAI_API_KEY — skipping module report card generation")
        return None

    if not conversation_log:
        logger.warning("No conversation log — skipping module report card generation")
        return None

    # Build transcript string — clean stutter artifacts and deduplicate
    transcript_lines = []
    prev_line = ""
    for msg in conversation_log:
        role = "STUDENT" if msg.get("role") == "agent" else "COACH"
        content = msg.get("content", "")[:800]  # Trim very long messages
        # Clean any remaining stutter artifacts
        if role == "STUDENT":
            content = _clean_transcript_text(content)
        line = f"{role}: {content}"
        # Skip duplicate consecutive lines
        if line == prev_line:
            continue
        transcript_lines.append(line)
        prev_line = line
    transcript = "\n".join(transcript_lines[-50:])  # Last 50 turns max

    total_turns = student_turns + coach_turns
    session_status = "Completed (full lesson)" if session_qualified else "Ended early (incomplete)"

    prompt = _MODULE_REPORT_PROMPT.format(
        module_name=module_name,
        module_key=module_key,
        duration_seconds=duration_seconds,
        total_turns=total_turns,
        student_turns=student_turns,
        coach_turns=coach_turns,
        session_status=session_status,
        transcript=transcript,
    )

    try:
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        response = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "grok-3-fast"),
            max_tokens=2500,
            temperature=0.4,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate the session report card JSON now."},
            ],
        )

        raw_text = response.choices[0].message.content.strip()

        # Parse JSON — strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[: raw_text.rfind("```")]

        report = json.loads(raw_text)

        # Ensure required fields exist
        report.setdefault("overall_score", 50)
        report.setdefault("overall_grade", "C")
        report.setdefault("summary", "Session completed.")
        report.setdefault("strengths", [])
        report.setdefault("areas_for_improvement", [])
        report.setdefault("key_moments", [])
        report.setdefault("homework", [])
        report.setdefault("coach_notes", "")

        # Add metadata
        report["module_key"] = module_key
        report["module_name"] = module_name
        report["duration_seconds"] = duration_seconds
        report["total_turns"] = total_turns
        report["session_qualified"] = session_qualified

        logger.info(
            "[MODULE REPORT] Generated report card: %s | score=%s grade=%s",
            module_key, report["overall_score"], report["overall_grade"],
        )

        return report

    except json.JSONDecodeError as e:
        logger.error("Failed to parse module report card JSON: %s", e)
        return None
    except Exception as e:
        logger.error("Module report card generation failed: %s", e)
        return None
