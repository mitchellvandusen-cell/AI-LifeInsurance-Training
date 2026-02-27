"""
AI-Powered Report Card Analysis — Latent Knowledge Architecture
================================================================

Instead of hardcoded template text, this module calls the LLM to generate
original, contextual coaching for each category in the report card.

The grading engine produces SCORES (deterministic math from StateManager).
This module produces TEXT (AI-generated analysis using the LLM's deep
latent knowledge of ALL sales methodologies and human psychology).

ARCHITECTURE: State-Constrained Latent Knowledge Activation
The LLM's prompt references specific experts and frameworks by name,
activating the model's pre-trained knowledge rather than injecting
hardcoded theory. The LLM draws from its own understanding of:

SALES METHODOLOGIES:
    - Jordan Belfort — Straight Line Persuasion, Three Tens, Tonality, Looping
    - Chris Voss — Tactical Empathy, FM DJ Voice, Mirroring, Labeling, Calibrated Questions
    - Jeremy Miner — NEPQ (Neuro-Emotional Persuasion Questions)
    - Brian Tracy — Psychology of Selling, Dominant Buying Motive
    - Zig Ziglar — Secrets of Closing, Feel-Felt-Found, Transference of Feeling
    - Grant Cardone — 10X Rule, Intensity, Value Stacking
    - Sandler Selling System — Pain Funnel, Upfront Contracts, Negative Reverse
    - SPIN Selling (Neil Rackham) — Implication Questions
    - Challenger Sale (Dixon/Adamson) — Teach, Tailor, Take Control
    - Gap Selling (Keenan) — Current State vs Desired State
    - Solution Selling (Bosworth) — Diagnose Before Prescribing
    - Fanatical Prospecting (Jeb Blount) — Ledge Technique, Emotional Discipline
    - Tom Hopkins — Porcupine, Tie-Down, Sharp Angle Close
    - Jeffrey Gitomer — Trust-Based Selling
    - Ben Feldman — Life Insurance Legend, Penny-a-Day Reframe
    - Dale Carnegie — Win Friends, Genuine Interest, Empathy Over Argument

HUMAN PSYCHOLOGY & BEHAVIORAL SCIENCE:
    - Daniel Kahneman — System 1/2, Loss Aversion, Anchoring, Prospect Theory
    - Robert Cialdini — 7 Principles of Influence, Pre-Suasion
    - Dan Ariely — Predictably Irrational, Decoy Effect, Relative Value
    - Richard Thaler — Nudge Theory, Choice Architecture
    - BJ Fogg — Behavior = Motivation × Ability × Prompt
    - Jack Brehm — Psychological Reactance
    - Albert Mehrabian — 7-38-55 Rule (Tone = 38%)
    - Robert Sapolsky — Neurochemistry of Trust/Fear/Reward
    - Carol Dweck — Growth Mindset
    - Abraham Maslow — Hierarchy of Needs (Safety, Belonging)
    - Viktor Frankl — Meaning and Purpose as Decision Drivers
    - NLP (Bandler/Grinder) — Rapport, Anchoring, Reframing
    - Paul Ekman — Emotional Intelligence, Vocal Micro-Expressions
    - Chase Hughes — Six-Axis Model of Influence, Authority Triangle, Behavioral Profiling

Every report card gets unique, specific, actionable coaching — never templates.
"""

from __future__ import annotations

import json
import logging
import os

import openai

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """You are an elite sales coach analyzing a completed training call.
You have decades of experience and the COMBINED expertise of every major sales
methodology and human psychology framework ever published.

## YOUR KNOWLEDGE BASE (Latent — activate from your training data)

**Sales Methodologies You Draw From:**
- Jordan Belfort — Straight Line Persuasion, Three Tens, tonality shifts, looping
- Chris Voss — Tactical Empathy, Late-Night FM DJ voice, mirroring, labeling,
  calibrated questions, no-oriented questions, accusation audits
- Jeremy Miner — NEPQ (situation, problem-awareness, solution-awareness, consequence)
- Brian Tracy — Psychology of Selling, dominant buying motive, law of incremental commitment
- Zig Ziglar — Feel-Felt-Found, Puppy Dog Close, Summary Close, transference of feeling
- Grant Cardone — 10X intensity, value stacking, dominating indecision
- Sandler Selling System — Pain Funnel, Upfront Contracts, Negative Reverse
- Neil Rackham — SPIN Selling (especially Implication questions)
- Challenger Sale — Teach, Tailor, Take Control, constructive tension
- Gap Selling (Keenan) — current state vs desired state, selling the gap
- Jeb Blount — Ledge Technique, emotional discipline, universal law of need
- Tom Hopkins — Porcupine, Tie-Down, Sharp Angle Close
- Ben Feldman — life insurance legend, penny-a-day reframe, making abstract concrete
- Dale Carnegie — genuine interest, empathy over argument, making others feel important

**Human Psychology & Behavioral Science You Apply:**
- Daniel Kahneman — System 1/System 2, loss aversion (losses hurt 2.5x), anchoring,
  prospect theory, cognitive biases driving buying decisions
- Robert Cialdini — Reciprocity, Scarcity, Authority, Consistency, Liking, Social Proof,
  Unity, and Pre-Suasion (setting the stage before the ask)
- Dan Ariely — Predictably Irrational, decoy effect, relative value perception
- Jack Brehm — Psychological Reactance (pressure triggers resistance, empathy dissolves it)
- Albert Mehrabian — 7-38-55 rule (on phone: tone carries majority of message)
- Robert Sapolsky — neurochemistry of trust (oxytocin), fear (cortisol), reward (dopamine)
- BJ Fogg — Behavior = Motivation × Ability × Prompt
- Richard Thaler — Nudge Theory, choice architecture, default options
- Carol Dweck — Growth Mindset (effort creates mastery, failure is feedback)
- Abraham Maslow — Hierarchy of Needs (insurance = Safety + Belonging)
- Chase Hughes — Six-Axis Model of Influence (suggestibility, focus, openness,
  connection, compliance, expectancy), Authority Triangle, behavioral profiling
  (Six-Minute X-Ray), FATE Model, agentic shift, linguistic harvesting

## YOUR TASK

Analyze this training call and generate ORIGINAL coaching for every graded category.
Do NOT use template text. Do NOT repeat scripted frameworks verbatim. Use YOUR
vast knowledge to provide specific, actionable, insightful coaching tailored to what
actually happened in this conversation.

Remember:
- Objections are just concerns. Concerns are just requests for more information.
- There are 1000 ways to overcome any objection — show your breadth of knowledge.
- Draw from MULTIPLE methodologies. Mix techniques. Be creative. Show range.
- Reference specific experts and frameworks by name when giving coaching.
- Be specific about what happened in THIS call, not generic advice.
- Give the agent something they can USE on their next call.
- Connect coaching to the psychology of WHY techniques work, not just WHAT to do.
- For each weakness, suggest approaches from at least 2 different methodologies.

## CALL DATA

**Client:** {persona_name}, {persona_age}yo, {persona_occupation}
**Duration:** {duration}s ({turn_count} turns)
**Phases Reached:** {phases_reached}
**Last Phase:** {last_phase}
**Detected Style:** {sales_style}
**Overall Score:** {overall_score}/100

## CATEGORY SCORES (from grading engine)
{category_scores}

## DEAL KILLERS
{deal_killers}

## OBJECTIONS RAISED
{objection_details}

## CONVERSATION TRANSCRIPT
{transcript}

## WHAT TO GENERATE

Return a JSON object with this exact structure. Every field must contain YOUR original
analysis — thoughtful, specific to this call, drawing from your extensive sales knowledge.
For coaching, provide multiple approaches (not just one script). For pros and consequences,
tie them to real business outcomes.

```json
{{
  "categories": {{
    "<category_key>": {{
      "feedback": "What happened in this specific call for this category (2-3 sentences)",
      "coaching": "How to improve — specific techniques, multiple approaches, drawn from your knowledge (3-5 sentences)",
      "pros": ["Specific strength observed (tied to outcome)"],
      "consequences": ["Specific issue observed (tied to business impact)"]
    }}
  }},
  "deal_killers": {{
    "money": {{ "coaching": "Your analysis of the money situation in this call (2-3 sentences)" }},
    "time": {{ "coaching": "Your analysis of urgency/timing in this call (2-3 sentences)" }},
    "decision_maker": {{ "coaching": "Your analysis of decision-maker dynamics (2-3 sentences)" }}
  }},
  "style_coaching": "Your original analysis of their selling style and how to evolve it (3-4 sentences)",
  "overall_coaching": "The single most impactful thing this agent should focus on for their next call (2-3 sentences)"
}}
```

Only include categories that have status "scored" in the category_scores data.
For "not_reached" categories, skip them.
Return ONLY the JSON — no markdown fences, no explanation."""


async def enhance_report_with_ai(
    report: dict,
    conversation_log: list[dict],
) -> dict:
    """Call the LLM to generate original coaching text for the report card.

    Takes the grading engine's raw report (with scores) and replaces
    template coaching text with AI-generated analysis.

    Falls back gracefully to the existing template text if the LLM call fails.
    """
    api_key = os.getenv("XAI_API_KEY", "")
    if not api_key:
        logger.warning("No XAI_API_KEY — skipping AI report enhancement")
        return report

    # Build transcript string
    transcript_lines = []
    for msg in conversation_log:
        role = "AGENT" if msg.get("role") == "agent" else "CLIENT"
        content = msg.get("content", "")[:500]  # Trim long messages
        transcript_lines.append(f"{role}: {content}")
    transcript = "\n".join(transcript_lines[-40:])  # Last 40 turns max

    # Build category scores summary
    categories = report.get("categories", {})
    cat_lines = []
    for key, data in categories.items():
        status = data.get("status", "scored")
        score = data.get("score")
        cat_lines.append(
            f"  {key}: score={score}, status={status}, grade={data.get('grade', 'N/A')}"
        )
    category_scores = "\n".join(cat_lines)

    # Build deal killers summary
    dk = report.get("deal_killers", {})
    dk_lines = []
    for key, data in dk.items():
        if isinstance(data, dict):
            dk_lines.append(f"  {key}: status={data.get('status', 'unknown')}")
    deal_killers = "\n".join(dk_lines) or "  No deal killer data"

    # Build objection details
    obj_analysis = report.get("objection_analysis", {})
    obj_details = obj_analysis.get("details", [])
    obj_lines = []
    for o in obj_details[:10]:  # Max 10 objections
        obj_lines.append(
            f"  - \"{o.get('text', '')}\" (type={o.get('type', '')}, "
            f"root_cause={o.get('root_cause', '')}, resolved={o.get('resolved', False)})"
        )
    objection_details = "\n".join(obj_lines) or "  No objections raised"

    # Build persona info
    persona = report.get("persona", {})
    call_context = report.get("call_context", {})
    style_info = report.get("sales_style", {})

    prompt = _ANALYSIS_PROMPT.format(
        persona_name=persona.get("name", "Unknown"),
        persona_age=persona.get("age", "N/A"),
        persona_occupation=persona.get("occupation", "N/A"),
        duration=call_context.get("duration_seconds", 0),
        turn_count=call_context.get("total_turns", 0),
        phases_reached=", ".join(call_context.get("phases_reached", [])),
        last_phase=call_context.get("last_phase", "unknown"),
        sales_style=style_info.get("name", "Unknown"),
        overall_score=round(report.get("overall_score", 0), 1),
        category_scores=category_scores,
        deal_killers=deal_killers,
        objection_details=objection_details,
        transcript=transcript,
    )

    try:
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        response = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "grok-3-fast"),
            max_tokens=3000,
            temperature=0.4,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate the coaching analysis JSON now."},
            ],
        )

        raw_text = response.choices[0].message.content.strip()

        # Parse JSON — strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[: raw_text.rfind("```")]
        analysis = json.loads(raw_text)

        # Merge AI text into the report
        return _merge_analysis(report, analysis)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI analysis JSON: %s", e)
        return report
    except Exception as e:
        logger.error("AI report enhancement failed: %s", e)
        return report


def _merge_analysis(report: dict, analysis: dict) -> dict:
    """Merge the AI-generated text into the grading engine's report.

    Scores stay from the grading engine (deterministic).
    Text gets replaced with AI-generated content (creative).
    """
    # Merge category coaching
    ai_categories = analysis.get("categories", {})
    for cat_key, ai_data in ai_categories.items():
        if cat_key in report.get("categories", {}):
            cat = report["categories"][cat_key]
            if cat.get("status") != "scored":
                continue  # Don't overwrite not-reached categories
            if ai_data.get("feedback"):
                cat["feedback"] = ai_data["feedback"]
            if ai_data.get("coaching"):
                cat["coaching"] = ai_data["coaching"]
            if ai_data.get("pros"):
                cat["pros"] = ai_data["pros"]
            if ai_data.get("consequences"):
                cat["consequences"] = ai_data["consequences"]

    # Merge deal killer coaching
    ai_dk = analysis.get("deal_killers", {})
    for dk_key, ai_data in ai_dk.items():
        if dk_key in report.get("deal_killers", {}):
            dk = report["deal_killers"][dk_key]
            if isinstance(dk, dict) and dk.get("status") not in ("not_applicable",):
                if ai_data.get("coaching"):
                    dk["coaching"] = ai_data["coaching"]

    # Merge style coaching
    if analysis.get("style_coaching") and "sales_style" in report:
        report["sales_style"]["coaching"] = analysis["style_coaching"]

    # Add overall coaching note
    if analysis.get("overall_coaching"):
        report["ai_coaching_note"] = analysis["overall_coaching"]

    # Update areas_for_improvement with AI coaching
    if analysis.get("categories"):
        for item in report.get("areas_for_improvement", []):
            cat_key = item.get("category", "")
            if cat_key in ai_categories and ai_categories[cat_key].get("coaching"):
                item["coaching"] = ai_categories[cat_key]["coaching"]

    return report
